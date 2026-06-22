from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Thesis, Category, Subcategory, IncludedPaper, Reference
from app.providers.common import MetadataError
from app.services.metadata_lookup import lookup_metadata_candidates, lookup_metadata_url

app = FastAPI(
    title="Prehospitala Avhandlingar",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/theses")
def get_theses(db: Session = Depends(get_db)):
    theses = db.query(Thesis).order_by(Thesis.running_number).all()
    return theses


@app.get("/theses/{running_number}")
def get_thesis(running_number: int, db: Session = Depends(get_db)):
    thesis = (
        db.query(Thesis)
        .filter(Thesis.running_number == running_number)
        .first()
    )
    return thesis


@app.patch("/theses/{running_number}")
def update_thesis_metadata(
    running_number: int,
    metadata: dict,
    db: Session = Depends(get_db),
):
    thesis = get_thesis_or_404(running_number, db)
    allowed_fields = {"abstract", "dissertation_url", "pdf_url", "doi", "urn"}

    for field in allowed_fields:
        if field in metadata:
            value = metadata[field]
            if isinstance(value, str):
                value = value.strip() or None
            setattr(thesis, field, value)

    db.commit()
    db.refresh(thesis)
    return serialize_thesis(thesis)


@app.post("/theses/{running_number}/lookup-metadata")
def lookup_thesis_metadata(running_number: int, db: Session = Depends(get_db)):
    thesis = get_thesis_or_404(running_number, db)
    return lookup_metadata_candidates(thesis)


@app.post("/metadata/lookup-url")
def lookup_metadata_from_url(payload: dict):
    url = (payload.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    try:
        return lookup_metadata_url(url)
    except MetadataError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def get_thesis_or_404(running_number: int, db: Session):
    thesis = (
        db.query(Thesis)
        .filter(Thesis.running_number == running_number)
        .first()
    )
    if thesis is None:
        raise HTTPException(status_code=404, detail="Thesis not found")
    return thesis


def grouped_counts(db: Session, label_column, order_by_count=True, exclude_empty=True):
    query = (
        db.query(label_column.label("label"), func.count(Thesis.id).label("count"))
        .filter(label_column.isnot(None))
        .group_by(label_column)
    )
    if exclude_empty:
        query = query.filter(label_column != "")
    if order_by_count:
        query = query.order_by(func.count(Thesis.id).desc(), label_column.asc())
    else:
        query = query.order_by(label_column.asc())

    rows = query.all()
    return [{"label": label, "count": count} for label, count in rows]


@app.get("/stats/overview")
def get_stats_overview(db: Session = Depends(get_db)):
    total_theses, first_year, last_year = db.query(
        func.count(Thesis.id),
        func.min(Thesis.year),
        func.max(Thesis.year),
    ).one()
    universities = (
        db.query(func.count(distinct(Thesis.university)))
        .filter(Thesis.university.isnot(None))
        .filter(Thesis.university != "")
        .scalar()
    )
    categories = db.query(func.count(Category.id)).scalar()
    return {
        "total_theses": total_theses,
        "first_year": first_year,
        "last_year": last_year,
        "universities": universities,
        "categories": categories,
    }


@app.get("/stats/by-university")
def get_stats_by_university(db: Session = Depends(get_db)):
    return grouped_counts(db, Thesis.university)


@app.get("/stats/by-profession")
def get_stats_by_profession(db: Session = Depends(get_db)):
    return grouped_counts(db, Thesis.profession)


@app.get("/stats/by-category")
def get_stats_by_category(db: Session = Depends(get_db)):
    rows = (
        db.query(Category.name.label("label"), func.count(Thesis.id).label("count"))
        .join(Thesis, Thesis.category_id == Category.id)
        .group_by(Category.id, Category.name)
        .order_by(func.count(Thesis.id).desc(), Category.name.asc())
        .all()
    )
    return [{"label": label, "count": count} for label, count in rows]


@app.get("/stats/by-year")
def get_stats_by_year(db: Session = Depends(get_db)):
    return grouped_counts(db, Thesis.year, order_by_count=False, exclude_empty=False)


def serialize_thesis(thesis: Thesis):
    return {
        "id": thesis.id,
        "running_number": thesis.running_number,
        "author": thesis.author,
        "profession": thesis.profession,
        "university": thesis.university,
        "year": thesis.year,
        "title": thesis.title,
        "degree_type": thesis.degree_type,
        "category_id": thesis.category_id,
        "subcategory_id": thesis.subcategory_id,
        "source": thesis.source,
        "abstract": thesis.abstract,
        "dissertation_url": thesis.dissertation_url,
        "pdf_url": thesis.pdf_url,
        "doi": thesis.doi,
        "urn": thesis.urn,
    }


def serialize_paper(paper: IncludedPaper):
    return {
        "id": paper.id,
        "thesis_id": paper.thesis_id,
        "title": paper.title,
        "journal": paper.journal,
        "year": paper.year,
        "doi": paper.doi,
        "pubmed_id": paper.pubmed_id,
        "url": paper.url,
        "abstract": paper.abstract,
    }


def serialize_reference(reference: Reference):
    return {
        "id": reference.id,
        "number": reference.number,
        "text": reference.text,
    }


@app.get("/references")
def get_references(db: Session = Depends(get_db)):
    references = db.query(Reference).order_by(Reference.number).all()
    return [serialize_reference(reference) for reference in references]


@app.get("/theses/{running_number}/papers")
def get_included_papers(running_number: int, db: Session = Depends(get_db)):
    thesis = get_thesis_or_404(running_number, db)
    papers = (
        db.query(IncludedPaper)
        .filter(IncludedPaper.thesis_id == thesis.id)
        .order_by(IncludedPaper.year, IncludedPaper.id)
        .all()
    )
    return [serialize_paper(paper) for paper in papers]


@app.post("/theses/{running_number}/papers")
def create_included_paper(
    running_number: int,
    paper_data: dict,
    db: Session = Depends(get_db),
):
    thesis = get_thesis_or_404(running_number, db)
    title = paper_data.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="Paper title is required")

    paper = IncludedPaper(
        thesis_id=thesis.id,
        title=title,
        journal=paper_data.get("journal"),
        year=paper_data.get("year"),
        doi=paper_data.get("doi"),
        pubmed_id=paper_data.get("pubmed_id"),
        url=paper_data.get("url"),
        abstract=paper_data.get("abstract"),
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return serialize_paper(paper)


def serialize_research_area(category: Category, db: Session):
    subcategories = (
        db.query(Subcategory)
        .filter(Subcategory.category_id == category.id)
        .order_by(Subcategory.id)
        .all()
    )

    serialized_subcategories = []
    for subcategory in subcategories:
        theses = (
            db.query(Thesis)
            .filter(Thesis.subcategory_id == subcategory.id)
            .order_by(Thesis.running_number)
            .all()
        )
        serialized_subcategories.append(
            {
                "id": subcategory.id,
                "name": subcategory.name,
                "narrative_text": subcategory.narrative_text,
                "theses": [serialize_thesis(thesis) for thesis in theses],
            }
        )

    return {
        "id": category.id,
        "name": category.name,
        "narrative_text": category.narrative_text,
        "subcategories": serialized_subcategories,
    }


@app.get("/research-areas")
def get_research_areas(db: Session = Depends(get_db)):
    categories = db.query(Category).order_by(Category.id).all()
    return [serialize_research_area(category, db) for category in categories]


@app.get("/research-areas/{category_id}")
def get_research_area(category_id: str, db: Session = Depends(get_db)):
    category = db.get(Category, category_id.upper())
    if category is None:
        raise HTTPException(status_code=404, detail="Research area not found")
    return serialize_research_area(category, db)


@app.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).order_by(Category.id).all()
    return categories


@app.get("/subcategories")
def get_subcategories(db: Session = Depends(get_db)):
    subcategories = db.query(Subcategory).order_by(Subcategory.id).all()
    return subcategories
