import re
from pathlib import Path

from docx import Document
from sqlalchemy import inspect, text

from app.database import SessionLocal, engine
from app.models import Category, Subcategory


DOCX_PATH = Path(__file__).resolve().parents[3] / "data" / "raw" / "Rapport.docx"

CATEGORY_CHAPTER_RE = re.compile(r"^Kapitel\s+([A-I])$")
CATEGORY_HEADING_RE = re.compile(r"^([A-I])\.\s+(.+)$")
SUBCATEGORY_HEADING_RE = re.compile(r"^([A-I]\d+)\s+(.+)$")


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def should_skip_paragraph(text: str) -> bool:
    return text.isdigit() or text.startswith("Figur ") or text.startswith("Tabell ")


def should_stop_import(text: str) -> bool:
    return text.startswith("Avslut") or text.startswith("Referenser")


def ensure_narrative_columns():
    inspector = inspect(engine)
    columns_by_table = {
        table: {column["name"] for column in inspector.get_columns(table)}
        for table in ("categories", "subcategories")
    }

    with engine.begin() as connection:
        if "narrative_text" not in columns_by_table["categories"]:
            connection.execute(text("ALTER TABLE categories ADD COLUMN narrative_text TEXT"))
        if "narrative_text" not in columns_by_table["subcategories"]:
            connection.execute(text("ALTER TABLE subcategories ADD COLUMN narrative_text TEXT"))


def get_or_create_category(db, category_id: str, name: str):
    category = db.get(Category, category_id)
    if category is None:
        category = Category(id=category_id, name=name)
        db.add(category)
    else:
        category.name = name
    return category


def get_or_create_subcategory(db, subcategory_id: str, name: str):
    subcategory = db.get(Subcategory, subcategory_id)
    if subcategory is None:
        subcategory = Subcategory(
            id=subcategory_id,
            name=name,
            category_id=subcategory_id[0],
        )
        db.add(subcategory)
    else:
        subcategory.name = name
        subcategory.category_id = subcategory_id[0]
    return subcategory


def append_text(buffers, key, paragraph_text):
    if key:
        buffers.setdefault(key, []).append(paragraph_text)


def import_narrative_text():
    ensure_narrative_columns()

    document = Document(DOCX_PATH)
    db = SessionLocal()

    category_text = {}
    subcategory_text = {}
    started = False
    current_category_id = None
    current_subcategory_id = None
    pending_category_id = None

    try:
        for paragraph in document.paragraphs:
            paragraph_text = clean(paragraph.text)
            if not paragraph_text:
                continue

            if should_stop_import(paragraph_text):
                break

            if should_skip_paragraph(paragraph_text):
                continue

            chapter_match = CATEGORY_CHAPTER_RE.match(paragraph_text)
            if chapter_match:
                category_id = chapter_match.group(1)
                if category_id == "A":
                    started = True

                if started:
                    pending_category_id = category_id
                    current_category_id = None
                    current_subcategory_id = None
                continue

            if not started:
                continue

            category_match = CATEGORY_HEADING_RE.match(paragraph_text)
            if category_match:
                category_id = category_match.group(1)
                category_name = category_match.group(2)
                get_or_create_category(db, category_id, category_name)
                current_category_id = category_id
                current_subcategory_id = None
                pending_category_id = None
                continue

            if pending_category_id:
                get_or_create_category(db, pending_category_id, paragraph_text)
                current_category_id = pending_category_id
                current_subcategory_id = None
                pending_category_id = None
                continue

            subcategory_match = SUBCATEGORY_HEADING_RE.match(paragraph_text)
            if subcategory_match:
                subcategory_id = subcategory_match.group(1)
                subcategory_name = subcategory_match.group(2)
                get_or_create_subcategory(db, subcategory_id, subcategory_name)
                current_category_id = subcategory_id[0]
                current_subcategory_id = subcategory_id
                continue

            if current_subcategory_id:
                append_text(subcategory_text, current_subcategory_id, paragraph_text)
            else:
                append_text(category_text, current_category_id, paragraph_text)

        for category in db.query(Category).all():
            category.narrative_text = "\n\n".join(category_text.get(category.id, [])) or None

        for subcategory in db.query(Subcategory).all():
            subcategory.narrative_text = (
                "\n\n".join(subcategory_text.get(subcategory.id, [])) or None
            )

        db.commit()

        categories_with_text = sum(bool(paragraphs) for paragraphs in category_text.values())
        subcategories_with_text = sum(bool(paragraphs) for paragraphs in subcategory_text.values())
        print(f"Categories with narrative text: {categories_with_text}")
        print(f"Subcategories with narrative text: {subcategories_with_text}")
    finally:
        db.close()


if __name__ == "__main__":
    import_narrative_text()
