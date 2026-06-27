import unittest
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from app.database import Base
from app.models import DiscoveryCandidate, Thesis
from app.providers import avhandlingar
from app.providers import diva
from app.providers.common import SearchQuery
from app.services.discovery import (
    approve_discovery_candidate,
    classify_duplicate,
    discovery_summary,
    discover_candidates,
    in_year_range,
    is_likely_dissertation_record,
    known_person_matches_record,
    known_person_query_variants,
    list_discovery_candidates,
    match_ems_keywords,
    person_name_from_known_person_input,
    reject_discovery_candidate,
    search_diva_hosts,
    search_known_person_source,
    source_rank,
    normalized_discovery_results,
)


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


CARINA_URL = "https://lnu.diva-portal.org/smash/record.jsf?pid=diva2%3A432398"
CARINA_TITLE = (
    "Akut omhändertagande: i mötet mellan patienter, närstående och olika professioner "
    "på skadeplats och på akutmottagning"
)
FIXTURES = Path(__file__).parent / "fixtures"


def carina_record(**overrides):
    data = {
        "title": CARINA_TITLE,
        "author": "Elmqvist, Carina",
        "university": "Linnaeus University",
        "year": 2011,
        "source": "DiVA",
        "source_host": "lnu.diva-portal.org",
        "source_url": CARINA_URL,
        "dissertation_url": CARINA_URL,
        "publication_type": "dissertation",
        "keywords": "Nursing",
        "abstract": "The overall aim was to describe acute care encounters at the scene of injury and in the emergency department.",
        "urn": "urn:nbn:se:lnu:diva-13643",
    }
    data.update(overrides)
    return data


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self._db_sessions = []
        self._db_engines = []

    def tearDown(self):
        for session in self._db_sessions:
            session.close()
        for engine in self._db_engines:
            engine.dispose()

    def make_db(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        self._db_engines.append(engine)
        self._db_sessions.append(session)
        return session

    def test_keyword_filter_matches_title_and_abstract(self):
        record = {
            "title": "Emergency dispatch and ambulance care",
            "abstract": "A thesis about out-of-hospital cardiac arrest.",
        }

        matches = match_ems_keywords(record, ["ambulance", "ohca", "primary care"])

        self.assertEqual(matches, ["ambulance"])

    def test_hanna_title_matches_prehospital_criteria(self):
        record = {
            "title": "Emergency visualized : exploring visual technology for paramedic-physician collaboration in emergency care",
        }

        matches = match_ems_keywords(record, ["paramedic", "emergency care"])

        self.assertEqual(matches, ["paramedic", "emergency care"])

    def test_keyword_filter_does_not_depend_on_abstract_extraction(self):
        record = {
            "title": "Decision support in emergency care",
            "abstract": "A thesis about ambulance care.",
        }

        matches = match_ems_keywords(record, ["ambulance"])

        self.assertEqual(matches, [])

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

    def test_author_order_year_and_university_identify_existing_thesis(self):
        record = {
            "title": "Non conveyance within the Swedish ambulance service",
            "author": "Höglund, Erik",
            "university": "Örebro University",
            "year": 2022,
        }

        result = classify_duplicate(record, [thesis(urn=None, dissertation_url=None)])

        self.assertEqual(result["match_status"], "already_in_database")
        self.assertEqual(result["matched_existing_running_number"], 128)

    def test_duplicate_matching_works_without_year_when_title_author_university_match(self):
        record = {
            "title": "Non conveyance within the Swedish ambulance service",
            "author": "Höglund, Erik",
            "university": "Örebro University",
            "year": None,
        }

        result = classify_duplicate(record, [thesis(urn=None, dissertation_url=None)])

        self.assertEqual(result["match_status"], "already_in_database")

    def test_new_candidate_when_similarity_is_low(self):
        record = {
            "title": "Leadership in municipal elder care",
            "author": "Someone Else",
            "university": "Lund University",
            "year": 2024,
        }

        result = classify_duplicate(record, [thesis()])

        self.assertEqual(result["match_status"], "new_candidate")

    def test_article_record_is_not_likely_dissertation(self):
        record = {
            "title": "Ambulance care in a journal article",
            "source": "journal article",
            "dissertation_url": "https://example.test/article",
        }

        self.assertFalse(is_likely_dissertation_record(record))

    def test_known_person_diva_search_scans_all_known_hosts(self):
        calls = []
        hanna_url = "https://hb.diva-portal.org/smash/record.jsf?pid=diva2%3A877048"

        def fake_search_host(host, query, limit):
            calls.append(host)
            if host == "hb.diva-portal.org":
                return [{
                    "title": "Emergency visualized : exploring visual technology for paramedic-physician collaboration in emergency care",
                    "author": "Hanna Maurin Söderholm",
                    "university": "Högskolan i Borås",
                    "year": 2015,
                    "source": "DiVA",
                    "source_host": host,
                    "dissertation_url": hanna_url,
                    "publication_type": "dissertation",
                }]
            return []

        with patch("app.services.discovery.diva.search_host", side_effect=fake_search_host):
            records = search_diva_hosts(SearchQuery(author="Hanna Maurin Söderholm"), 5)

        self.assertTrue(calls)
        self.assertIn("hb.diva-portal.org", calls)
        self.assertEqual(records[0]["dissertation_url"], hanna_url)
        self.assertNotIn("umu.diva-portal.org", calls)

    def test_repository_sources_rank_above_libris_for_same_thesis(self):
        self.assertGreater(source_rank("avhandlingar.se", "openarchive.ki.se"), source_rank("DiVA", "hb.diva-portal.org"))
        self.assertGreater(source_rank("DiVA", "hb.diva-portal.org"), source_rank("SwePub", None))
        self.assertGreater(source_rank("SwePub", None), source_rank("LIBRIS", None))

    def test_avhandlingar_missing_year_is_allowed(self):
        self.assertTrue(in_year_range({"source": "avhandlingar.se", "year": None}, 2024, 2026, allow_missing_year=True))
        self.assertFalse(in_year_range({"source": "DiVA", "year": None}, 2024, 2026))

    def test_avhandlingar_candidate_prefers_canonical_repository_url(self):
        html = """
        <html>
          <head><meta property="og:title" content="Emergency care thesis by Fredrik Bursell"></head>
          <body>
            <a href="https://openarchive.ki.se/articles/thesis/example">Repository</a>
            <span>University:</span><strong>Karolinska Institutet</strong>
            <span>Year:</span><strong>2024</strong>
          </body>
        </html>
        """

        with patch("app.providers.avhandlingar.fetch_text", return_value=html):
            candidate = avhandlingar.record_candidate(
                "https://www.avhandlingar.se/avhandling/example",
                SearchQuery(author="Fredrik Bursell"),
            )

        self.assertEqual(candidate["dissertation_url"], "https://openarchive.ki.se/articles/thesis/example")
        self.assertEqual(candidate["source_host"], "openarchive.ki.se")

    def test_avhandlingar_hanna_page_parses_author_university_and_keywords(self):
        html = """
        <html>
          <body>
            <h1>Emergency visualized : exploring visual technology for paramedic-physician collaboration in emergency care</h1>
            Författare: <a>Hanna Maurin Söderholm</a> ; <a>Högskolan I Borås</a> ; []
            Nyckelord: <a>3D video</a> ; <a>emergency care</a> ; <a>paramedic</a> ; <a>pre-hospital care</a> ;
            Sammanfattning: This thesis explores collaboration in emergency care.
            <a href="https://hb.diva-portal.org/smash/get/diva2:877048/FULLTEXT01">fulltext</a>
          </body>
        </html>
        """

        with patch("app.providers.avhandlingar.fetch_text", return_value=html):
            candidate = avhandlingar.record_candidate(
                "https://www.avhandlingar.se/avhandling/44cc4967bb/",
                SearchQuery(author="Hanna Maurin Söderholm"),
            )

        self.assertEqual(candidate["title"], "Emergency visualized : exploring visual technology for paramedic-physician collaboration in emergency care")
        self.assertEqual(candidate["author"], "Hanna Maurin Söderholm")
        self.assertEqual(candidate["university"], "Högskolan I Borås")
        self.assertIn("paramedic", candidate["keywords"])
        self.assertIn("pre-hospital care", candidate["keywords"])

    def test_avhandlingar_page_parser_is_generic_for_author_university_keywords(self):
        html = """
        <html>
          <body>
            <h1>Pre-hospital teamwork in rural emergency care</h1>
            Författare: <a>Karin Åström Berg</a> ; <a>Umeå universitet</a> ; []
            Nyckelord: <a>ambulance</a> ; <a>pre-hospital care</a> ; <a>emergency medical services</a> ;
            Sammanfattning: A dissertation about rural ambulance teamwork.
          </body>
        </html>
        """

        with patch("app.providers.avhandlingar.fetch_text", return_value=html):
            candidate = avhandlingar.record_candidate(
                "https://www.avhandlingar.se/avhandling/example/",
                SearchQuery(author="Karin Åström Berg"),
            )

        self.assertEqual(candidate["title"], "Pre-hospital teamwork in rural emergency care")
        self.assertEqual(candidate["author"], "Karin Åström Berg")
        self.assertEqual(candidate["university"], "Umeå universitet")
        self.assertIn("pre-hospital care", candidate["keywords"])

    def test_diva_author_order_matches_hanna_search(self):
        record = {
            "title": "Emergency visualized : exploring visual technology for paramedic-physician collaboration in emergency care",
            "author": "Maurin Söderholm, Hanna",
            "university": "Högskolan i Borås",
            "source": "DiVA",
            "source_host": "hb.diva-portal.org",
            "dissertation_url": "https://hb.diva-portal.org/smash/record.jsf?pid=diva2%3A877048",
            "publication_type": "dissertation",
            "keywords": "paramedic, pre-hospital care",
        }

        self.assertTrue(is_likely_dissertation_record(record))
        self.assertTrue(match_ems_keywords(record, ["paramedic", "pre-hospital care"]))
        self.assertTrue(known_person_matches_record("Hanna Maurin Söderholm", record))

    def test_diva_author_order_matching_is_generic(self):
        record = {
            "title": "Pre-hospital teamwork in rural emergency care",
            "author": "Åström Berg, Karin",
            "university": "Umeå universitet",
            "source": "DiVA",
            "dissertation_url": "https://umu.diva-portal.org/smash/record.jsf?pid=diva2:1",
            "publication_type": "dissertation",
            "keywords": "ambulance, pre-hospital care",
        }

        self.assertTrue(known_person_matches_record("Karin Åström Berg", record))
        self.assertTrue(known_person_matches_record("Karin Berg", record))
        self.assertTrue(known_person_matches_record("Åström Berg Karin", record))

    def test_known_person_discovery_stops_after_avhandlingar_result(self):
        db = SimpleNamespace(
            query=lambda model: SimpleNamespace(all=lambda: []),
            commit=lambda: None,
            add=lambda candidate: None,
        )
        calls = []
        hanna = {
            "title": "Emergency visualized : exploring visual technology for paramedic-physician collaboration in emergency care",
            "author": "Hanna Maurin Söderholm",
            "university": "Högskolan i Borås",
            "year": None,
            "source": "avhandlingar.se",
            "source_host": "hb.diva-portal.org",
            "source_url": "https://hb.diva-portal.org/smash/record.jsf?pid=diva2%3A877048",
            "dissertation_url": "https://hb.diva-portal.org/smash/record.jsf?pid=diva2%3A877048",
        }

        def fake_search_source(source_name, term, known_person, university, limit):
            calls.append(source_name)
            if source_name == "avhandlingar":
                return [hanna]
            return [{"title": "Article-level result", "source": "journal article"}]

        with (
            patch("app.services.discovery.search_source", side_effect=fake_search_source),
            patch("app.services.discovery.upsert_discovery_candidate"),
        ):
            result = discover_candidates(
                db,
                {
                    "known_person": "Hanna Maurin Söderholm",
                    "source": "all",
                    "year_from": "2024",
                    "keyword_group": "all",
                },
            )

        self.assertEqual(result["stored"], 1)
        self.assertEqual(calls, ["avhandlingar"])

    def test_known_person_query_variants_cover_hanna_spellings(self):
        variants = known_person_query_variants("Hanna_Maurin-Söderholm")

        self.assertIn("hanna maurin söderholm", variants)
        self.assertIn("hanna söderholm", variants)
        self.assertIn("söderholm thesis", variants)
        self.assertIn('"maurin söderholm"', variants)

    def test_known_person_input_strips_year_and_university_text(self):
        self.assertEqual(
            person_name_from_known_person_input("Hanna Maurin Söderholm 2013 högskolan i borås"),
            "hanna maurin söderholm",
        )

    def test_hanna_known_person_variants_return_avhandlingar_dissertation_first(self):
        hanna = {
            "title": "Emergency visualized : exploring visual technology for paramedic-physician collaboration in emergency care",
            "author": "Hanna Maurin Söderholm",
            "university": "Högskolan i Borås",
            "year": None,
            "source": "avhandlingar.se",
            "source_host": "hb.diva-portal.org",
            "source_url": "https://hb.diva-portal.org/smash/record.jsf?pid=diva2%3A877048",
            "dissertation_url": "https://hb.diva-portal.org/smash/record.jsf?pid=diva2%3A877048",
        }

        for query_name in [
            "Hanna Maurin Söderholm",
            "Hanna Söderholm",
            "Hanna_Maurin_Söderholm",
            "Maurin Söderholm",
            "Hanna Maurin Söderholm 2013 högskolan i borås",
        ]:
            with self.subTest(query_name=query_name):
                db = SimpleNamespace(
                    query=lambda model: SimpleNamespace(all=lambda: []),
                    commit=lambda: None,
                    add=lambda candidate: None,
                )
                saved_payloads = []

                def fake_avhandlingar_search(query, limit=5):
                    query_text = query.as_text().lower()
                    if "söderholm" in query_text:
                        return [hanna]
                    return []

                with (
                    patch("app.services.discovery.avhandlingar.search", side_effect=fake_avhandlingar_search),
                    patch("app.services.discovery.search_diva_hosts") as diva_search,
                    patch("app.services.discovery.upsert_discovery_candidate", side_effect=lambda db, payload: saved_payloads.append(payload)),
                ):
                    result = discover_candidates(
                        db,
                        {
                            "known_person": query_name,
                            "source": "all",
                            "year_from": "2024",
                            "keyword_group": "all",
                        },
                    )

                self.assertEqual(result["stored"], 1)
                self.assertEqual(saved_payloads[0]["title"], hanna["title"])
                self.assertEqual(saved_payloads[0]["university"], "Högskolan i Borås")
                diva_search.assert_not_called()

    def test_known_person_discovery_filter_path_does_not_crash_on_author_tokens(self):
        hanna = {
            "title": "Emergency visualized : exploring visual technology for paramedic-physician collaboration in emergency care",
            "author": "Hanna Maurin Söderholm",
            "university": "Högskolan i Borås",
            "year": None,
            "source": "avhandlingar.se",
            "source_host": "hb.diva-portal.org",
            "source_url": "https://hb.diva-portal.org/smash/record.jsf?pid=diva2%3A877048",
            "dissertation_url": "https://hb.diva-portal.org/smash/record.jsf?pid=diva2%3A877048",
            "keywords": "paramedic, pre-hospital care",
        }

        for query_name in ["Hanna Maurin Söderholm", "Hanna Söderholm"]:
            with self.subTest(query_name=query_name):
                db = SimpleNamespace(
                    query=lambda model: SimpleNamespace(all=lambda: []),
                    commit=lambda: None,
                    add=lambda candidate: None,
                )
                saved_payloads = []

                with (
                    patch("app.services.discovery.search_source", return_value=[hanna]),
                    patch("app.services.discovery.upsert_discovery_candidate", side_effect=lambda db, payload: saved_payloads.append(payload)),
                ):
                    result = discover_candidates(
                        db,
                        {
                            "known_person": query_name,
                            "source": "avhandlingar",
                            "year_from": "2024",
                            "keyword_group": "all",
                        },
                    )

                self.assertEqual(result["stored"], 1)
                self.assertEqual(saved_payloads[0]["author"], "Hanna Maurin Söderholm")

    def test_diva_known_person_search_stops_after_first_found_variant(self):
        calls = []
        hanna = {
            "title": "Emergency visualized : exploring visual technology for paramedic-physician collaboration in emergency care",
            "author": "Maurin Söderholm, Hanna",
            "source": "DiVA",
            "source_host": "hb.diva-portal.org",
            "dissertation_url": "https://hb.diva-portal.org/smash/record.jsf?pid=diva2%3A877048",
            "publication_type": "dissertation",
            "keywords": "paramedic, pre-hospital care",
        }

        def fake_search_diva_hosts(query, limit):
            calls.append(query.author)
            return [hanna] if query.author == "hanna maurin söderholm" else []

        with patch("app.services.discovery.search_diva_hosts", side_effect=fake_search_diva_hosts):
            records = search_known_person_source("diva", "Hanna Maurin Söderholm", "", 5)

        self.assertEqual(records, [hanna])
        self.assertEqual(calls, ["hanna maurin söderholm"])

    def test_carina_known_person_variants_return_lnu_diva_dissertation(self):
        for query_name in [
            "Carina Elmqvist",
            "Carina E",
            "Elmqvist, Carina",
            "carina elmqvist",
            "   Carina   Elmqvist   ",
        ]:
            with self.subTest(query_name=query_name):
                db = self.make_db()

                def fake_search_host(host, query, limit):
                    if host == "lnu.diva-portal.org":
                        return [carina_record()]
                    return []

                with (
                    patch("app.services.discovery.avhandlingar.search", return_value=[]),
                    patch("app.services.discovery.diva.search_host", side_effect=fake_search_host),
                ):
                    result = discover_candidates(
                        db,
                        {
                            "known_person": query_name,
                            "source": "all",
                            "keyword_group": "all",
                            "show_known_matches": True,
                        },
                    )

                candidates = list_discovery_candidates(
                    db,
                    {"status_filter": "active", "include_known": True},
                )
                self.assertEqual(result["stored"], 1)
                self.assertEqual(candidates[0].source_url, CARINA_URL)
                self.assertEqual(candidates[0].year, 2011)
                self.assertEqual(candidates[0].author, "Elmqvist, Carina")
                self.assertEqual(candidates[0].abstract, carina_record()["abstract"])

    def test_carina_person_search_uses_author_field_not_title_or_abstract(self):
        record = carina_record(title="A title without the searched person", abstract="")

        self.assertTrue(known_person_matches_record("Carina Elmqvist", record))
        self.assertTrue(known_person_matches_record("Carina E", record))
        self.assertTrue(known_person_matches_record("C Elmqvist", record))
        self.assertTrue(known_person_matches_record("Elmqvist C", record))

    def test_carina_full_search_filters_unrelated_thesis_without_crashing(self):
        db = self.make_db()
        unrelated = carina_record(
            title="Emergency Department Triage in Sweden",
            author="Wireklint, Sara",
            urn="urn:nbn:se:lnu:diva-99999",
        )
        unrelated["source_url"] = "https://lnu.diva-portal.org/smash/record.jsf?pid=diva2%3A99999"
        unrelated["dissertation_url"] = unrelated["source_url"]

        with (
            patch("app.services.discovery.avhandlingar.search", return_value=[]),
            patch(
                "app.services.discovery.diva.search_host",
                return_value=[carina_record(), unrelated],
            ),
        ):
            result = discover_candidates(
                db,
                {
                    "known_person": "Carina Elmqvist",
                    "source": "all",
                    "show_known_matches": True,
                },
            )

        self.assertEqual(result["stored"], 1)
        self.assertEqual(result["discovered"], 1)

    def test_carina_initial_query_variant_reaches_full_discovery_path(self):
        db = self.make_db()
        calls = []

        def fake_search_host(host, query, limit):
            calls.append(query.author)
            if host == "lnu.diva-portal.org" and query.author == "carina e*":
                return [carina_record()]
            return []

        with (
            patch("app.services.discovery.avhandlingar.search", return_value=[]),
            patch("app.services.discovery.diva.search_host", side_effect=fake_search_host),
        ):
            result = discover_candidates(
                db,
                {
                    "known_person": "Carina E",
                    "source": "all",
                    "keyword_group": "all",
                    "show_known_matches": True,
                },
            )

        candidates = list_discovery_candidates(db, {"status_filter": "active", "include_known": True})
        self.assertIn("carina e*", calls)
        self.assertEqual(result["stored"], 1)
        self.assertEqual(candidates[0].source_url, CARINA_URL)

    def test_carina_person_search_is_not_limited_by_recent_year_window(self):
        db = self.make_db()

        with (
            patch("app.services.discovery.avhandlingar.search", return_value=[]),
            patch("app.services.discovery.diva.search_host", return_value=[carina_record()]),
        ):
            discover_candidates(
                db,
                {
                    "known_person": "Carina Elmqvist",
                    "source": "all",
                    "year_from": "2024",
                    "keyword_group": "all",
                    "show_known_matches": True,
                },
            )

        candidates = list_discovery_candidates(db, {"status_filter": "active", "include_known": True})
        self.assertEqual(candidates[0].year, 2011)

    def test_carina_person_search_is_not_blocked_by_missing_prehospital_keyword(self):
        db = self.make_db()

        with (
            patch("app.services.discovery.avhandlingar.search", return_value=[]),
            patch("app.services.discovery.diva.search_host", return_value=[carina_record(keywords="", title="Nursing encounters")]),
        ):
            result = discover_candidates(
                db,
                {
                    "known_person": "Carina Elmqvist",
                    "source": "all",
                    "keyword_group": "english",
                    "show_known_matches": True,
                },
            )

        self.assertEqual(result["stored"], 1)

    def test_carina_already_in_database_is_returned_when_known_matches_are_included(self):
        db = self.make_db()
        db.add(
            Thesis(
                running_number=20,
                title=CARINA_TITLE,
                author="Carina Elmqvist",
                university="Linnaeus University",
                year=2011,
                dissertation_url=CARINA_URL,
                urn="urn:nbn:se:lnu:diva-13643",
                classification_status="classified",
            )
        )
        db.commit()

        with (
            patch("app.services.discovery.avhandlingar.search", return_value=[]),
            patch("app.services.discovery.diva.search_host", return_value=[carina_record()]),
        ):
            discover_candidates(
                db,
                {
                    "known_person": "Carina Elmqvist",
                    "source": "all",
                    "keyword_group": "all",
                    "show_known_matches": True,
                },
            )

        candidates = list_discovery_candidates(db, {"status_filter": "active", "include_known": True})
        self.assertEqual(candidates[0].match_status, "already_in_database")

    def test_known_database_match_stays_visible_even_with_handled_review_status(self):
        db = self.make_db()
        db.add(
            DiscoveryCandidate(
                title=CARINA_TITLE,
                author="Carina Elmqvist",
                year=2011,
                source="DiVA",
                source_url=CARINA_URL,
                matched_keywords="[]",
                match_status="already_in_database",
                review_status="approved",
                relevance_status="approved",
            )
        )
        db.commit()

        candidates = list_discovery_candidates(db, {"status_filter": "active", "include_known": True})

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].match_status, "already_in_database")

    def test_approved_summary_counts_only_candidates_that_created_theses(self):
        db = self.make_db()
        db.add_all(
            [
                DiscoveryCandidate(
                    title="Legacy approved candidate",
                    author="Legacy Author",
                    source="DiVA",
                    match_status="new_candidate",
                    review_status="approved",
                    relevance_status="approved",
                ),
                DiscoveryCandidate(
                    title="Created thesis candidate",
                    author="Created Author",
                    source="DiVA",
                    match_status="new_candidate",
                    review_status="approved",
                    relevance_status="approved",
                    created_thesis_id=132,
                    created_thesis_running_number=132,
                ),
            ]
        )
        db.commit()

        self.assertEqual(discovery_summary(db)["approved_new_theses"], 1)

    def test_legacy_approved_candidate_without_created_thesis_is_reopened_and_enriched(self):
        db = self.make_db()
        db.add(
            DiscoveryCandidate(
                title=CARINA_TITLE.replace("Akut omhändertagande:", "Akut omhändertagande :"),
                author="Elmqvist, Carina, 1964-",
                year=2011,
                source="LIBRIS",
                source_url="http://libris.kb.se/bib/12280122",
                matched_keywords="[]",
                match_status="new_candidate",
                review_status="approved",
                relevance_status="approved",
            )
        )
        db.commit()

        with (
            patch("app.services.discovery.avhandlingar.search", return_value=[]),
            patch("app.services.discovery.diva.search_host", return_value=[carina_record()]),
        ):
            discover_candidates(
                db,
                {
                    "known_person": "Carina Elmqvist",
                    "source": "all",
                    "keyword_group": "all",
                    "show_known_matches": True,
                },
            )

        candidates = list_discovery_candidates(db, {"status_filter": "active", "include_known": True})
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].source, "DiVA")
        self.assertEqual(candidates[0].source_url, CARINA_URL)
        self.assertEqual(candidates[0].abstract, carina_record()["abstract"])
        self.assertEqual(candidates[0].relevance_status, "pending")

    def test_carina_possible_duplicate_is_returned_instead_of_hidden(self):
        db = self.make_db()
        db.add(
            Thesis(
                running_number=21,
                title="Akut omhändertagande i mötet mellan patienter och närstående",
                author="Carina Elmqvist",
                university="Linnaeus University",
                year=2011,
                classification_status="classified",
            )
        )
        db.commit()

        with (
            patch("app.services.discovery.avhandlingar.search", return_value=[]),
            patch("app.services.discovery.diva.search_host", return_value=[carina_record(urn=None)]),
        ):
            discover_candidates(
                db,
                {
                    "known_person": "Carina Elmqvist",
                    "source": "all",
                    "keyword_group": "all",
                    "show_known_matches": True,
                },
            )

        candidates = list_discovery_candidates(db, {"status_filter": "active", "include_known": True})
        self.assertEqual(candidates[0].match_status, "possible_duplicate")

    def test_diva_author_query_variants_include_family_given_and_comma_format(self):
        variants = known_person_query_variants("Carina Elmqvist")

        self.assertIn("carina elmqvist", variants)
        self.assertIn('"carina elmqvist"', variants)
        self.assertIn("elmqvist, carina", variants)
        self.assertIn("carina AND elmqvist", variants)
        self.assertIn("elmqvist", variants)

    def test_carina_fixture_exercises_query_parse_normalize_and_deduplicate(self):
        db = self.make_db()
        results_html = (FIXTURES / "diva_carina_results.html").read_text()
        record_html = (FIXTURES / "diva_carina_record.html").read_text()

        def fake_fetch(url, params=None):
            return results_html if "resultList.jsf" in url else record_html

        with (
            patch("app.services.discovery.avhandlingar.search", return_value=[]),
            patch("app.providers.diva.fetch_text", side_effect=fake_fetch),
        ):
            result = discover_candidates(
                db,
                {
                    "known_person": "carina   elmqvist",
                    "source": "all",
                    "show_known_matches": True,
                },
            )

        self.assertEqual(len(result["candidates"]), 1)
        self.assertEqual(result["candidates"][0]["diva_id"], "diva2:432398")
        self.assertEqual(result["candidates"][0]["publication_year"], 2011)

    def test_direct_diva_url_and_identifier_use_same_candidate_pipeline(self):
        for reference in [CARINA_URL, "diva2:432398", "https://lnu.diva-portal.org/smash/record.jsf?pid=diva2:432398"]:
            db = self.make_db()
            with patch("app.services.discovery.diva.lookup_url", return_value=carina_record()):
                result = discover_candidates(
                    db,
                    {"known_person": reference, "source": "all", "show_known_matches": True},
                )

            self.assertEqual(len(result["candidates"]), 1)
            self.assertEqual(result["candidates"][0]["diva_id"], "diva2:432398")

    def test_provider_failure_does_not_hide_diva_candidate(self):
        db = self.make_db()
        with (
            patch("app.services.discovery.avhandlingar.search", side_effect=RuntimeError("provider failed")),
            patch("app.services.discovery.diva.search_host", return_value=[carina_record()]),
        ):
            result = discover_candidates(
                db,
                {"known_person": "Elmqvist, Carina", "source": "all", "show_known_matches": True},
            )

        self.assertEqual(result["candidates"][0]["diva_id"], "diva2:432398")
        self.assertEqual(result["errors"][0]["source"], "avhandlingar")

    def test_discovery_response_deduplicates_same_diva_record_from_two_sources(self):
        diva_candidate = carina_record()
        other_source = {
            **diva_candidate,
            "source": "SwePub",
            "source_url": CARINA_URL,
        }

        results = normalized_discovery_results([diva_candidate, other_source])

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["diva_id"], "diva2:432398")
        self.assertEqual(results[0]["sources"], ["DiVA", "SwePub"])

    def test_diva_known_person_scans_beyond_first_page_limit_before_dissertation_filter(self):
        links = "".join(
            f'<a href="/smash/record.jsf?pid=diva2%3A{i}">Record {i}</a>'
            for i in range(1, 10)
        )
        links += '<a href="/smash/record.jsf?pid=diva2%3A432398">Carina</a>'

        def fake_record_candidate(record_url, query):
            if "432398" in record_url:
                return carina_record(dissertation_url=record_url, source_url=record_url)
            return {
                "title": "Article result",
                "author": "Elmqvist, Carina",
                "source": "DiVA",
                "publication_type": "article",
                "dissertation_url": record_url,
            }

        with (
            patch("app.providers.diva.fetch_text", return_value=links),
            patch("app.providers.diva.record_candidate", side_effect=fake_record_candidate),
        ):
            records = diva.search_host("lnu.diva-portal.org", SearchQuery(author="Carina Elmqvist"), 8)

        self.assertEqual(records[0]["source_url"], "https://lnu.diva-portal.org/smash/record.jsf?pid=diva2%3A432398")

    def test_lnu_host_is_in_unknown_university_diva_scan(self):
        calls = []

        def fake_search_host(host, query, limit):
            calls.append(host)
            return [carina_record()] if host == "lnu.diva-portal.org" else []

        with patch("app.services.discovery.diva.search_host", side_effect=fake_search_host):
            records = search_diva_hosts(SearchQuery(author="Carina Elmqvist"), 8)

        self.assertIn("lnu.diva-portal.org", calls)
        self.assertEqual(records[0]["source_url"], CARINA_URL)

    def test_reject_candidate_hides_from_active_list_without_creating_thesis(self):
        db = self.make_db()
        db.add(
            Thesis(
                running_number=131,
                title="Existing thesis",
                author="Existing Author",
                classification_status="needs_classification",
            )
        )
        candidate = DiscoveryCandidate(
            title="Pre-hospital teamwork in rural emergency care",
            author="Karin Åström Berg",
            university="Umeå universitet",
            source="DiVA",
            source_url="https://umu.diva-portal.org/smash/record.jsf?pid=diva2:1",
            matched_keywords='["pre-hospital care"]',
            match_status="new_candidate",
            review_status="needs_review",
            relevance_status="pending",
        )
        db.add(candidate)
        db.commit()

        self.assertEqual(len(list_discovery_candidates(db, {"status_filter": "active"})), 1)

        reject_discovery_candidate(db, candidate)

        self.assertEqual(len(list_discovery_candidates(db, {"status_filter": "active"})), 0)
        self.assertEqual(len(list_discovery_candidates(db, {"status_filter": "rejected"})), 1)
        self.assertEqual(db.query(Thesis).count(), 1)

    def test_approve_candidate_creates_thesis_and_hides_from_active_list(self):
        db = self.make_db()
        db.add(
            Thesis(
                running_number=131,
                title="Existing thesis",
                author="Existing Author",
                classification_status="needs_classification",
            )
        )
        candidate = DiscoveryCandidate(
            title="Emergency visualized : exploring visual technology for paramedic-physician collaboration in emergency care",
            author="Hanna Maurin Söderholm",
            university="Högskolan i Borås",
            year=None,
            abstract="This thesis explores collaboration in emergency care.",
            source="DiVA",
            source_host="hb.diva-portal.org",
            source_url="https://hb.diva-portal.org/smash/record.jsf?pid=diva2%3A877048",
            pdf_url="https://hb.diva-portal.org/smash/get/diva2:877048/FULLTEXT01",
            publication_type="comprehensiveDoctoralThesis",
            matched_keywords='["paramedic", "pre-hospital care"]',
            match_status="new_candidate",
            review_status="needs_review",
            relevance_status="pending",
        )
        db.add(candidate)
        db.commit()

        saved = approve_discovery_candidate(db, candidate)
        thesis_row = db.query(Thesis).filter(Thesis.running_number == 132).one()

        self.assertEqual(saved.relevance_status, "approved")
        self.assertEqual(saved.created_thesis_running_number, 132)
        self.assertEqual(thesis_row.title, candidate.title)
        self.assertEqual(thesis_row.author, "Hanna Maurin Söderholm")
        self.assertEqual(thesis_row.university, "Högskolan i Borås")
        self.assertIsNone(thesis_row.year)
        self.assertEqual(thesis_row.dissertation_url, candidate.source_url)
        self.assertEqual(thesis_row.pdf_url, candidate.pdf_url)
        self.assertEqual(thesis_row.abstract, candidate.abstract)
        self.assertEqual(thesis_row.degree_type, "Doktorsavhandling")
        self.assertIsNone(thesis_row.category_id)
        self.assertIsNone(thesis_row.subcategory_id)
        self.assertEqual(thesis_row.classification_status, "needs_classification")
        self.assertEqual(len(list_discovery_candidates(db, {"status_filter": "active"})), 0)
        self.assertEqual(len(list_discovery_candidates(db, {"status_filter": "approved"})), 1)

    def test_approve_candidate_rejects_known_database_match(self):
        db = self.make_db()
        candidate = DiscoveryCandidate(
            title="Known thesis",
            author="Known Author",
            source="DiVA",
            match_status="already_in_database",
            review_status="needs_review",
            relevance_status="pending",
        )
        db.add(candidate)
        db.commit()

        with self.assertRaises(ValueError):
            approve_discovery_candidate(db, candidate)

        self.assertEqual(db.query(Thesis).count(), 0)

    def test_possible_duplicate_requires_explicit_confirmation_before_approval(self):
        db = self.make_db()
        candidate = DiscoveryCandidate(
            title="Pre-hospital teamwork in rural emergency care",
            author="Karin Åström Berg",
            source="DiVA",
            match_status="possible_duplicate",
            review_status="needs_review",
            relevance_status="pending",
        )
        db.add(candidate)
        db.commit()

        with self.assertRaises(ValueError):
            approve_discovery_candidate(db, candidate)

        self.assertEqual(db.query(Thesis).count(), 0)

        approve_discovery_candidate(db, candidate, confirm_duplicate=True)

        self.assertEqual(db.query(Thesis).count(), 1)

    def test_backend_duplicate_check_blocks_accidental_duplicate_approval(self):
        db = self.make_db()
        db.add(
            Thesis(
                running_number=131,
                title="Emergency visualized : exploring visual technology for paramedic-physician collaboration in emergency care",
                author="Hanna Maurin Söderholm",
                university="Högskolan i Borås",
                classification_status="needs_classification",
            )
        )
        candidate = DiscoveryCandidate(
            title="Emergency visualized : exploring visual technology for paramedic-physician collaboration in emergency care",
            author="Maurin Söderholm, Hanna",
            university="Högskolan i Borås",
            source="DiVA",
            source_url="https://hb.diva-portal.org/smash/record.jsf?pid=diva2%3A877048",
            matched_keywords='["paramedic"]',
            match_status="new_candidate",
            review_status="needs_review",
            relevance_status="pending",
        )
        db.add(candidate)
        db.commit()

        with self.assertRaises(ValueError):
            approve_discovery_candidate(db, candidate)

        self.assertEqual(db.query(Thesis).count(), 1)
        self.assertEqual(candidate.match_status, "already_in_database")


if __name__ == "__main__":
    unittest.main()
