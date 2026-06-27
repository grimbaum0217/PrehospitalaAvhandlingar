from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import distinct, func, text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.database import Base
from app.database import engine
from app.auth import COOKIE_NAME, SiteAuthMiddleware, handle_login, login_page
from app.config import load_settings
from app.models import Thesis, Category, Subcategory, IncludedPaper, Reference, DiscoveryCandidate
from app.providers.common import MetadataError
from app.services.discovery import (
    approve_discovery_candidate,
    discover_candidates,
    discovery_summary,
    list_discovery_candidates,
    mark_discovery_candidate_needs_review,
    reject_discovery_candidate,
    serialize_discovery_candidate,
)
from app.services.metadata_lookup import lookup_metadata_candidates, lookup_metadata_url

METADATA_STATUSES = {
    "not_started",
    "candidate_found",
    "accepted",
    "not_found",
    "needs_review",
}


def utcnow():
    return datetime.now(timezone.utc)


def normalize_profession(value):
    return " ".join(str(value or "").strip().split())


def profession_key(value):
    return normalize_profession(value).casefold()


def existing_professions(db: Session) -> list[str]:
    rows = (
        db.query(Thesis.profession)
        .filter(Thesis.profession.isnot(None))
        .filter(Thesis.profession != "")
        .distinct()
        .order_by(Thesis.profession)
        .all()
    )
    return [profession for (profession,) in rows]


def resolve_profession(db: Session, value, allow_new=False) -> str:
    profession = normalize_profession(value)
    if not profession:
        raise HTTPException(status_code=400, detail="profession is required")

    for existing in existing_professions(db):
        if profession_key(existing) == profession_key(profession):
            return existing

    if allow_new:
        return profession
    raise HTTPException(status_code=400, detail="Unknown profession")


def ensure_metadata_workflow_columns(bind=engine):
    Base.metadata.create_all(bind=bind)
    with bind.begin() as connection:
        thesis_columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(theses)")).fetchall()
        }
        if "metadata_status" not in thesis_columns:
            connection.execute(
                text(
                    "ALTER TABLE theses ADD COLUMN metadata_status "
                    "VARCHAR NOT NULL DEFAULT 'not_started'"
                )
            )
        if "metadata_last_checked_at" not in thesis_columns:
            connection.execute(
                text("ALTER TABLE theses ADD COLUMN metadata_last_checked_at DATETIME")
            )
        if "classification_status" not in thesis_columns:
            connection.execute(
                text("ALTER TABLE theses ADD COLUMN classification_status VARCHAR")
            )
            connection.execute(
                text(
                    "UPDATE theses "
                    "SET classification_status = 'classified' "
                    "WHERE category_id IS NOT NULL AND subcategory_id IS NOT NULL"
                )
            )
        discovery_columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(discovery_candidates)")).fetchall()
        }
        if "source_host" not in discovery_columns:
            connection.execute(text("ALTER TABLE discovery_candidates ADD COLUMN source_host VARCHAR"))
        if "publication_type" not in discovery_columns:
            connection.execute(text("ALTER TABLE discovery_candidates ADD COLUMN publication_type VARCHAR"))
        if "relevance_status" not in discovery_columns:
            connection.execute(
                text(
                    "ALTER TABLE discovery_candidates ADD COLUMN relevance_status "
                    "VARCHAR NOT NULL DEFAULT 'pending'"
                )
            )
            connection.execute(
                text(
                    "UPDATE discovery_candidates "
                    "SET relevance_status = review_status "
                    "WHERE review_status IN ('approved', 'rejected', 'needs_review')"
                )
            )
        if "created_thesis_id" not in discovery_columns:
            connection.execute(text("ALTER TABLE discovery_candidates ADD COLUMN created_thesis_id INTEGER"))
        if "created_thesis_running_number" not in discovery_columns:
            connection.execute(
                text("ALTER TABLE discovery_candidates ADD COLUMN created_thesis_running_number INTEGER")
            )


ensure_metadata_workflow_columns()

app = FastAPI(
    title="Prehospitala Avhandlingar",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/theses")
def get_theses(db: Session = Depends(get_db)):
    theses = db.query(Thesis).order_by(Thesis.year.desc(), Thesis.running_number.desc()).all()
    return theses


@app.get("/theses/needs-classification")
def get_theses_needing_classification(db: Session = Depends(get_db)):
    theses = (
        db.query(Thesis)
        .filter(Thesis.classification_status == "needs_classification")
        .filter(Thesis.category_id.is_(None))
        .filter(Thesis.subcategory_id.is_(None))
        .order_by(Thesis.running_number)
        .all()
    )
    return [serialize_thesis(thesis) for thesis in theses]


@app.get("/professions")
def get_professions(db: Session = Depends(get_db)):
    return existing_professions(db)


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

    if "profession" in metadata:
        thesis.profession = resolve_profession(
            db,
            metadata.get("profession"),
            allow_new=bool(metadata.get("allow_new_profession")),
        )

    for field in allowed_fields:
        if field in metadata:
            value = metadata[field]
            if isinstance(value, str):
                value = value.strip() or None
            setattr(thesis, field, value)

    thesis.metadata_status = "accepted"
    db.commit()
    db.refresh(thesis)
    return serialize_thesis(thesis)


@app.patch("/theses/{running_number}/classification")
def classify_thesis(
    running_number: int,
    payload: dict,
    db: Session = Depends(get_db),
):
    category_id = (payload.get("category_id") or "").strip()
    subcategory_id = (payload.get("subcategory_id") or "").strip()
    profession = resolve_profession(
        db,
        payload.get("profession"),
        allow_new=bool(payload.get("allow_new_profession")),
    )
    if not category_id:
        raise HTTPException(status_code=400, detail="category_id is required")
    if not subcategory_id:
        raise HTTPException(status_code=400, detail="subcategory_id is required")

    thesis = get_thesis_or_404(running_number, db)
    category = db.get(Category, category_id)
    subcategory = db.get(Subcategory, subcategory_id)
    if category is None:
        raise HTTPException(status_code=400, detail="Unknown category_id")
    if subcategory is None:
        raise HTTPException(status_code=400, detail="Unknown subcategory_id")
    if subcategory.category_id != category.id:
        raise HTTPException(
            status_code=400,
            detail="subcategory_id does not belong to category_id",
        )

    thesis.category_id = category.id
    thesis.subcategory_id = subcategory.id
    thesis.profession = profession
    thesis.classification_status = "classified"
    db.commit()
    db.refresh(thesis)
    return serialize_thesis(thesis)


@app.post("/theses/{running_number}/lookup-metadata")
def lookup_thesis_metadata(running_number: int, db: Session = Depends(get_db)):
    thesis = get_thesis_or_404(running_number, db)
    try:
        result = lookup_metadata_candidates(thesis)
    except Exception as exc:  # Metadata lookup should not break the review workflow.
        result = {
            "search": {
                "title": thesis.title,
                "author": thesis.author,
                "university": thesis.university,
                "year": thesis.year,
            },
            "candidates": [],
            "errors": [{"source": "metadata_lookup", "error": str(exc)}],
            "error_summary": {
                "message": "Metadata lookup failed",
                "count": 1,
                "details": [{"source": "metadata_lookup", "error": str(exc)}],
            },
        }
    thesis.metadata_last_checked_at = utcnow()
    thesis.metadata_status = "candidate_found" if result["candidates"] else "not_found"
    db.commit()
    return result


@app.patch("/theses/{running_number}/metadata-status")
def update_thesis_metadata_status(
    running_number: int,
    payload: dict,
    db: Session = Depends(get_db),
):
    status = payload.get("metadata_status")
    if status not in METADATA_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid metadata status")

    thesis = get_thesis_or_404(running_number, db)
    thesis.metadata_status = status
    db.commit()
    db.refresh(thesis)
    return serialize_thesis(thesis)


@app.post("/metadata/lookup-url")
def lookup_metadata_from_url(payload: dict):
    url = (payload.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    try:
        return lookup_metadata_url(url)
    except MetadataError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/discovery/search")
def run_discovery_search(payload: dict, db: Session = Depends(get_db)):
    return discover_candidates(db, payload)


@app.get("/discovery/summary")
def get_discovery_summary(db: Session = Depends(get_db)):
    return discovery_summary(db)


@app.get("/discovery/candidates")
def get_discovery_candidates(
    match_status: str | None = None,
    review_status: str | None = None,
    status_filter: str = "active",
    include_known: bool = False,
    db: Session = Depends(get_db),
):
    candidates = list_discovery_candidates(
        db,
        {
            "match_status": match_status,
            "review_status": review_status,
            "status_filter": status_filter,
            "include_known": include_known,
        },
    )
    return [serialize_discovery_candidate(candidate) for candidate in candidates]


@app.patch("/discovery/candidates/{candidate_id}")
def update_discovery_candidate(candidate_id: int, payload: dict, db: Session = Depends(get_db)):
    review_status = payload.get("review_status")
    if review_status not in {"approved", "rejected", "needs_review"}:
        raise HTTPException(status_code=400, detail="Invalid review status")

    candidate = db.query(DiscoveryCandidate).filter(DiscoveryCandidate.id == candidate_id).first()
    if candidate is None:
        raise HTTPException(status_code=404, detail="Discovery candidate not found")

    try:
        if review_status == "approved":
            candidate = approve_discovery_candidate(
                db,
                candidate,
                confirm_duplicate=bool(payload.get("confirm_duplicate")),
            )
        elif review_status == "rejected":
            candidate = reject_discovery_candidate(db, candidate)
        else:
            candidate = mark_discovery_candidate_needs_review(db, candidate)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return serialize_discovery_candidate(candidate)


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
        "classification_status": thesis.classification_status,
        "source": thesis.source,
        "abstract": thesis.abstract,
        "dissertation_url": thesis.dissertation_url,
        "pdf_url": thesis.pdf_url,
        "doi": thesis.doi,
        "urn": thesis.urn,
        "metadata_status": thesis.metadata_status or "not_started",
        "metadata_last_checked_at": thesis.metadata_last_checked_at,
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


@app.get("/classification/options")
def get_classification_options(db: Session = Depends(get_db)):
    categories = db.query(Category).order_by(Category.id).all()
    return [
        {
            "id": category.id,
            "name": category.name,
            "subcategories": [
                {
                    "id": subcategory.id,
                    "name": subcategory.name,
                    "category_id": subcategory.category_id,
                }
                for subcategory in sorted(category.subcategories, key=lambda item: item.id)
            ],
        }
        for category in categories
    ]


@app.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).order_by(Category.id).all()
    return categories


@app.get("/subcategories")
def get_subcategories(db: Session = Depends(get_db)):
    subcategories = db.query(Subcategory).order_by(Subcategory.id).all()
    return subcategories


# The existing application remains the API implementation. A small outer app
# owns authentication and the production SPA, keeping every API route under
# one unambiguous prefix.
api_app = app
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


def create_application(api_application, app_settings, static_dir: Path = STATIC_DIR):
    application = FastAPI(
        title="Prehospitala Avhandlingar",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    application.state.settings = app_settings
    application.add_middleware(SiteAuthMiddleware, settings=app_settings)
    application.mount("/api", api_application)

    @application.get("/login")
    def get_login():
        return login_page()

    @application.post("/login")
    async def post_login(request: Request):
        return await handle_login(request, app_settings)

    @application.post("/logout")
    def logout():
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(COOKIE_NAME, path="/")
        return response

    index_path = static_dir / "index.html"
    assets_dir = static_dir / "assets"
    if assets_dir.is_dir():
        application.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @application.get("/{full_path:path}")
    def frontend(full_path: str):
        if static_dir.is_dir() and full_path:
            requested = (static_dir / full_path).resolve()
            if requested.is_relative_to(static_dir.resolve()) and requested.is_file():
                return FileResponse(requested)
        if index_path.is_file():
            return FileResponse(index_path)
        return {"status": "running", "frontend": "Use the Vite development server locally"}

    return application


settings = load_settings()
app = create_application(api_app, settings)
