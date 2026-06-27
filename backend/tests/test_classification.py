import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import (
    classify_thesis,
    ensure_metadata_workflow_columns,
    get_professions,
    get_stats_by_profession,
    get_theses_needing_classification,
    lookup_thesis_metadata,
    update_thesis_metadata,
)
from app.models import Category, DiscoveryCandidate, Subcategory, Thesis
from app.services.discovery import approve_discovery_candidate


class ClassificationEndpointTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()
        self.seed_data()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def seed_data(self):
        category_a = Category(id="A", name="Assessment")
        category_b = Category(id="B", name="Care")
        self.db.add_all(
            [
                category_a,
                category_b,
                Subcategory(id="A1", name="Dispatch", category=category_a),
                Subcategory(id="B1", name="Treatment", category=category_b),
                Thesis(
                    running_number=132,
                    title="Emergency visualized",
                    author="Hanna Maurin Söderholm",
                    university="Högskolan i Borås",
                    classification_status="needs_classification",
                ),
                Thesis(
                    running_number=10,
                    title="Old classified thesis",
                    author="Existing Author",
                    profession="Leg Ssk",
                    category_id="A",
                    subcategory_id="A1",
                    classification_status="classified",
                ),
                Thesis(
                    running_number=11,
                    title="Old categorized thesis with null status",
                    author="Existing Author",
                    profession="Leg Läk",
                    category_id="A",
                    subcategory_id="A1",
                    classification_status=None,
                ),
            ]
        )
        self.db.commit()

    def test_old_thesis_with_category_and_subcategory_is_not_in_queue(self):
        rows = get_theses_needing_classification(self.db)

        self.assertEqual([row["running_number"] for row in rows], [132])

    def test_old_thesis_with_null_status_and_existing_category_is_not_in_queue(self):
        rows = get_theses_needing_classification(self.db)

        self.assertNotIn(11, [row["running_number"] for row in rows])

    def test_valid_classification_sets_category_subcategory_and_status(self):
        data = classify_thesis(
            132,
            {"category_id": "A", "subcategory_id": "A1", "profession": "Leg Ssk"},
            self.db,
        )

        self.assertEqual(data["category_id"], "A")
        self.assertEqual(data["subcategory_id"], "A1")
        self.assertEqual(data["profession"], "Leg Ssk")
        self.assertEqual(data["classification_status"], "classified")

    def test_subcategory_from_wrong_category_is_blocked(self):
        with self.assertRaises(HTTPException) as raised:
            classify_thesis(
                132,
                {"category_id": "A", "subcategory_id": "B1", "profession": "Leg Ssk"},
                self.db,
            )

        self.assertEqual(raised.exception.status_code, 400)

    def test_missing_category_is_blocked(self):
        with self.assertRaises(HTTPException) as raised:
            classify_thesis(132, {"subcategory_id": "A1", "profession": "Leg Ssk"}, self.db)

        self.assertEqual(raised.exception.status_code, 400)

    def test_missing_subcategory_is_blocked(self):
        with self.assertRaises(HTTPException) as raised:
            classify_thesis(132, {"category_id": "A", "profession": "Leg Ssk"}, self.db)

        self.assertEqual(raised.exception.status_code, 400)

    def test_unknown_thesis_returns_404(self):
        with self.assertRaises(HTTPException) as raised:
            classify_thesis(
                999,
                {"category_id": "A", "subcategory_id": "A1", "profession": "Leg Ssk"},
                self.db,
            )

        self.assertEqual(raised.exception.status_code, 404)

    def test_needs_classification_list_removes_classified_thesis(self):
        before = get_theses_needing_classification(self.db)
        self.assertEqual([row["running_number"] for row in before], [132])

        classify_thesis(
            132,
            {"category_id": "A", "subcategory_id": "A1", "profession": "Leg Ssk"},
            self.db,
        )

        after = get_theses_needing_classification(self.db)
        self.assertEqual(after, [])

    def test_discovery_approved_thesis_appears_in_classification_queue(self):
        candidate = DiscoveryCandidate(
            title="New pre-hospital thesis",
            author="New Author",
            university="Lund University",
            source="DiVA",
            source_url="https://example.test/thesis",
            matched_keywords='["pre-hospital care"]',
            match_status="new_candidate",
            review_status="needs_review",
            relevance_status="pending",
        )
        self.db.add(candidate)
        self.db.commit()

        approve_discovery_candidate(self.db, candidate)

        rows = get_theses_needing_classification(self.db)
        self.assertIn(133, [row["running_number"] for row in rows])

    def test_existing_thesis_professions_are_unchanged_by_classification(self):
        before = {
            thesis.running_number: thesis.profession
            for thesis in self.db.query(Thesis).filter(Thesis.running_number.in_([10, 11])).all()
        }

        classify_thesis(
            132,
            {"category_id": "A", "subcategory_id": "A1", "profession": "Leg Ssk"},
            self.db,
        )

        after = {
            thesis.running_number: thesis.profession
            for thesis in self.db.query(Thesis).filter(Thesis.running_number.in_([10, 11])).all()
        }
        self.assertEqual(after, before)

    def test_profession_stats_still_use_existing_thesis_profession_field(self):
        stats = get_stats_by_profession(self.db)

        self.assertIn({"label": "Leg Ssk", "count": 1}, stats)
        self.assertIn({"label": "Leg Läk", "count": 1}, stats)

    def test_profession_can_be_selected_for_new_discovery_thesis(self):
        data = classify_thesis(
            132,
            {"category_id": "A", "subcategory_id": "A1", "profession": "Leg Läk"},
            self.db,
        )

        self.assertEqual(data["profession"], "Leg Läk")

    def test_new_classified_thesis_counts_under_selected_profession(self):
        classify_thesis(
            132,
            {"category_id": "A", "subcategory_id": "A1", "profession": "Leg Läk"},
            self.db,
        )

        stats = get_stats_by_profession(self.db)
        self.assertIn({"label": "Leg Läk", "count": 2}, stats)

    def test_profession_can_be_changed_in_thesis_edit(self):
        updated = update_thesis_metadata(
            10,
            {"profession": "Leg Läk"},
            self.db,
        )

        self.assertEqual(updated["profession"], "Leg Läk")

    def test_new_profession_can_be_added_to_central_list(self):
        updated = update_thesis_metadata(
            10,
            {"profession": "Socionom", "allow_new_profession": True},
            self.db,
        )

        self.assertEqual(updated["profession"], "Socionom")
        self.assertIn("Socionom", get_professions(self.db))

    def test_profession_duplicate_case_and_whitespace_reuses_existing_value(self):
        updated = update_thesis_metadata(
            10,
            {"profession": "  leg ssk  ", "allow_new_profession": True},
            self.db,
        )

        self.assertEqual(updated["profession"], "Leg Ssk")
        self.assertEqual(get_professions(self.db).count("Leg Ssk"), 1)

    def test_invalid_profession_is_blocked_by_backend(self):
        with self.assertRaises(HTTPException) as raised:
            classify_thesis(
                132,
                {"category_id": "A", "subcategory_id": "A1", "profession": "Ny profession"},
                self.db,
            )

        self.assertEqual(raised.exception.status_code, 400)

    def test_startup_does_not_set_existing_theses_to_needs_classification(self):
        ensure_metadata_workflow_columns(self.engine)

        classified = (
            self.db.query(Thesis)
            .filter(Thesis.running_number == 10)
            .one()
        )
        null_status = (
            self.db.query(Thesis)
            .filter(Thesis.running_number == 11)
            .one()
        )
        self.assertEqual(classified.classification_status, "classified")
        self.assertIsNone(null_status.classification_status)

    def test_missing_classification_status_migration_classifies_existing_categorized_theses(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TABLE theses ("
                    "id INTEGER PRIMARY KEY, "
                    "running_number INTEGER NOT NULL UNIQUE, "
                    "author VARCHAR NOT NULL, "
                    "title TEXT NOT NULL, "
                    "category_id VARCHAR, "
                    "subcategory_id VARCHAR)"
                )
            )
            connection.execute(
                text(
                    "CREATE TABLE categories ("
                    "id VARCHAR PRIMARY KEY, "
                    "name VARCHAR NOT NULL, "
                    "narrative_text TEXT)"
                )
            )
            connection.execute(
                text(
                    "CREATE TABLE subcategories ("
                    "id VARCHAR PRIMARY KEY, "
                    "name VARCHAR NOT NULL, "
                    "category_id VARCHAR, "
                    "narrative_text TEXT)"
                )
            )
            connection.execute(
                text(
                    "CREATE TABLE discovery_candidates ("
                    "id INTEGER PRIMARY KEY, "
                    "title TEXT NOT NULL, "
                    "source VARCHAR NOT NULL, "
                    "match_status VARCHAR NOT NULL DEFAULT 'new_candidate', "
                    "review_status VARCHAR NOT NULL DEFAULT 'needs_review')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO theses (running_number, author, title, category_id, subcategory_id) "
                    "VALUES (1, 'Existing Author', 'Existing Title', 'A', 'A1')"
                )
            )

        ensure_metadata_workflow_columns(engine)

        with engine.connect() as connection:
            status = connection.execute(
                text("SELECT classification_status FROM theses WHERE running_number = 1")
            ).scalar_one()

        engine.dispose()
        self.assertEqual(status, "classified")

    def test_metadata_lookup_returns_structured_error_instead_of_crashing(self):
        with patch("app.main.lookup_metadata_candidates", side_effect=RuntimeError("provider failed")):
            result = lookup_thesis_metadata(10, self.db)

        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["errors"][0]["source"], "metadata_lookup")
        self.assertIn("provider failed", result["errors"][0]["error"])


if __name__ == "__main__":
    unittest.main()
