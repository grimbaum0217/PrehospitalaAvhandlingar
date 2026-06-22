import unittest
from types import SimpleNamespace

from app.services.discovery import classify_duplicate, match_ems_keywords


def thesis(**overrides):
    data = {
        "id": 1,
        "running_number": 128,
        "title": "Non-conveyance within the Swedish ambulance service",
        "author": "Erik Höglund",
        "university": "Örebro Universitet",
        "year": 2022,
        "doi": None,
        "urn": "urn:nbn:se:oru:diva-97614",
        "dissertation_url": "https://oru.diva-portal.org/smash/record.jsf?pid=diva2:1639288",
        "pdf_url": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


class DiscoveryTests(unittest.TestCase):
    def test_keyword_filter_matches_title_and_abstract(self):
        record = {
            "title": "Emergency dispatch and ambulance care",
            "abstract": "A thesis about out-of-hospital cardiac arrest.",
        }

        matches = match_ems_keywords(record, ["ambulance", "ohca", "primary care"])

        self.assertEqual(matches, ["ambulance"])

    def test_exact_identifier_is_already_in_database(self):
        record = {
            "title": "Non conveyance within Swedish ambulance service",
            "author": "Höglund, Erik",
            "university": "Örebro University",
            "year": 2022,
            "urn": "urn:nbn:se:oru:diva-97614",
        }

        result = classify_duplicate(record, [thesis()])

        self.assertEqual(result["match_status"], "already_in_database")
        self.assertEqual(result["matched_existing_running_number"], 128)

    def test_possible_duplicate_when_title_is_similar(self):
        record = {
            "title": "Non-conveyance in the Swedish ambulance service",
            "author": "Unknown",
            "university": "Örebro Universitet",
            "year": 2022,
        }

        result = classify_duplicate(record, [thesis(urn=None, dissertation_url=None)])

        self.assertEqual(result["match_status"], "possible_duplicate")

    def test_new_candidate_when_similarity_is_low(self):
        record = {
            "title": "Leadership in municipal elder care",
            "author": "Someone Else",
            "university": "Lund University",
            "year": 2024,
        }

        result = classify_duplicate(record, [thesis()])

        self.assertEqual(result["match_status"], "new_candidate")


if __name__ == "__main__":
    unittest.main()
