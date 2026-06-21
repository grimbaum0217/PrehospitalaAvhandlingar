from sqlalchemy import inspect, text

from app.database import Base, engine
from app import models


THESIS_METADATA_COLUMNS = {
    "abstract": "TEXT",
    "dissertation_url": "VARCHAR",
    "pdf_url": "VARCHAR",
    "doi": "VARCHAR",
    "urn": "VARCHAR",
}


def prepare_metadata_schema():
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    thesis_columns = {column["name"] for column in inspector.get_columns("theses")}

    with engine.begin() as connection:
        for column_name, column_type in THESIS_METADATA_COLUMNS.items():
            if column_name not in thesis_columns:
                connection.execute(
                    text(f"ALTER TABLE theses ADD COLUMN {column_name} {column_type}")
                )

    print("Metadata schema prepared")


if __name__ == "__main__":
    prepare_metadata_schema()
