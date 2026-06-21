from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Thesis, Category, Subcategory

app = FastAPI(
    title="Prehospitala Avhandlingar",
    version="0.1.0"
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


@app.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).order_by(Category.id).all()
    return categories


@app.get("/subcategories")
def get_subcategories(db: Session = Depends(get_db)):
    subcategories = db.query(Subcategory).order_by(Subcategory.id).all()
    return subcategories