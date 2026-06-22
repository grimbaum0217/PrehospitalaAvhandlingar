import re
from pathlib import Path

from docx import Document

from app.database import Base, SessionLocal, engine
from app.models import Reference


DOCX_PATH = Path(__file__).resolve().parents[3] / "data" / "raw" / "Rapport.docx"


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def import_references():
    Base.metadata.create_all(bind=engine)

    document = Document(DOCX_PATH)
    db = SessionLocal()
    references = []
    in_references = False

    try:
        for paragraph in document.paragraphs:
            paragraph_text = clean(paragraph.text)
            if not paragraph_text:
                continue

            if paragraph_text == "Referenser":
                in_references = True
                continue

            if not in_references:
                continue

            if paragraph_text.startswith("Författare"):
                break

            references.append(paragraph_text)

        db.query(Reference).delete()
        for index, reference_text in enumerate(references, start=1):
            db.add(Reference(number=index, text=reference_text))

        db.commit()
        print(f"Imported references: {len(references)}")
    finally:
        db.close()


if __name__ == "__main__":
    import_references()
