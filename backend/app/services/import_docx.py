import re
from docx import Document

from app.database import Base, engine, SessionLocal
from app.models import Category, Subcategory, Thesis


DOCX_PATH = "../data/raw/Rapport.docx"


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_metadata(text: str):
    text = clean(text)

    match = re.match(
    r"^(\d+)\.\s*(.+?),\s*(.+?),\s*(.+?)\s+(\d{4})\s*\.?$",
    text,
)

    if not match:
        return None

    return {
        "running_number": int(match.group(1)),
        "author": clean(match.group(2)),
        "profession": clean(match.group(3)),
        "university": clean(match.group(4)),
        "year": int(match.group(5)),
    }


def import_docx():
    Base.metadata.create_all(bind=engine)

    doc = Document(DOCX_PATH)
    table = doc.tables[0]

    db = SessionLocal()

    current_category = None
    current_subcategory = None
    imported = 0
    skipped = []

    for row in table.rows:
        left = clean(row.cells[0].text)
        right = clean(row.cells[1].text)

        if not left:
            continue

        sub_match = re.match(r"^([A-I]\d)\s+(.+)$", left)
        cat_match = re.match(r"^([A-I])\s+(.+)$", left)
        thesis_match = re.match(r"^\d+\.", left)

        if sub_match:
            sub_id = sub_match.group(1)
            sub_name = clean(sub_match.group(2))

            current_subcategory = db.get(Subcategory, sub_id)
            if current_subcategory is None:
                current_subcategory = Subcategory(
                    id=sub_id,
                    name=sub_name,
                    category_id=current_category.id if current_category else sub_id[0],
                )
                db.add(current_subcategory)

        elif cat_match and left == right:
            cat_id = cat_match.group(1)
            cat_name = clean(cat_match.group(2))

            current_category = db.get(Category, cat_id)
            if current_category is None:
                current_category = Category(id=cat_id, name=cat_name)
                db.add(current_category)

            current_subcategory = None

        elif thesis_match:
            metadata = parse_metadata(left)

            if metadata is None:
                skipped.append(left)
                continue

            exists = (
                db.query(Thesis)
                .filter(Thesis.running_number == metadata["running_number"])
                .first()
            )

            if exists is None:
                thesis = Thesis(
                    running_number=metadata["running_number"],
                    author=metadata["author"],
                    profession=metadata["profession"],
                    university=metadata["university"],
                    year=metadata["year"],
                    title=right,
                    category_id=current_category.id if current_category else None,
                    subcategory_id=current_subcategory.id if current_subcategory else None,
                    source="Rapport.docx",
                )
                db.add(thesis)
                imported += 1

    db.commit()

    total = db.query(Thesis).count()

    db.close()

    print(f"Importerade nya poster: {imported}")
    print(f"Totalt antal avhandlingar i databasen: {total}")

    if skipped:
        print("\nKunde inte tolka dessa rader:")
        for s in skipped:
            print("-", s)


if __name__ == "__main__":
    import_docx()