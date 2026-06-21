from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Thesis, Category, Subcategory

from fastapi.middleware.cors import CORSMiddleware

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
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


@app.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).order_by(Category.id).all()
    return categories


@app.get("/subcategories")
def get_subcategories(db: Session = Depends(get_db)):
    subcategories = db.query(Subcategory).order_by(Subcategory.id).all()
    return subcategories
