import unittest
from unittest.mock import patch

from app.providers import diva
from app.providers.common import SearchQuery
from app.services.metadata_lookup import apply_diva_preference


ERIK_URL = "https://oru.diva-portal.org/smash/record.jsf?pid=diva2%3A1639288"
ULF_URL = "https://hb.diva-portal.org/smash/record.jsf?pid=diva2%3A0000001"
AGNES_URL = "https://hb.diva-portal.org/smash/record.jsf?pid=diva2%3A0000002"


def result_page(url):
    return f'<html><body><a href="{url}">record</a></body></html>'


def record_page(title, author, university, year, host, urn="urn:nbn:se:test:diva-1"):
    return f"""
    <html>
      <head>
        <title>{title}</title>
        <link rel="canonical" href="https://{host}/smash/record.jsf?pid=diva2:1" />
        <meta name="DC.Title" content="{title}">
        <meta name="DC.Creator" content="{author}">
        <meta name="DC.Description" content="A dissertation abstract.">
        <meta name="DC.Identifier.urn" content="{urn}">
        <meta name="DC.date" content="{year}">
        <meta name="DC.Publisher" content="{university}">
        <meta name="DC.Type" content="dissertation">
        <meta name="citation_title" content="{title}">
        <meta name="citation_author" content="{author}">
        <meta name="citation_publisher" content="{university}">
        <meta name="citation_publication_date" content="{year}">
        <meta name="citation_pdf_url" content="https://{host}/smash/get/diva2:1/FULLTEXT01">
      </head>
      <body></body>
    </html>
    """


class DivaLookupTests(unittest.TestCase):
    def test_direct_erik_hoglund_url_parses_metadata(self):
        html = record_page(
            "Non-conveyance within the Swedish ambulance service : A prehospital patient safety study",
            "Höglund, Erik",
            "Örebro University",
            2022,
            "oru.diva-portal.org",
            urn="urn:nbn:se:oru:diva-97614",
        )
        query = SearchQuery(
            title="Non-Conveyance within the Swedish ambulance service- A prehospital patient safety study.",
            author="Erik Höglund",
            university="Örebro Universitet",
            year=2022,
        )

        with patch("app.providers.diva.fetch_text", return_value=html):
            candidate = diva.lookup_url(ERIK_URL, query)

        self.assertEqual(candidate["source"], "DiVA")
        self.assertEqual(candidate["source_host"], "oru.diva-portal.org")
        self.assertEqual(candidate["author"], "Höglund, Erik")
        self.assertEqual(candidate["year"], 2022)
        self.assertEqual(candidate["urn"], "urn:nbn:se:oru:diva-97614")
        self.assertIn("FULLTEXT01", candidate["pdf_url"])
        self.assertGreaterEqual(candidate["confidence"], 0.9)

    def test_ulf_andersson_search_uses_boras_diva_host_first(self):
        query = SearchQuery(
            title="Clinical reasoning among emergency medical service clinicians. An iterative and fragmented process involving the collaborative effort(s) of many.",
            author="Ulf Andersson",
            university="Högskolan i Borås",
            year=2023,
        )
        calls = []

        def fake_fetch(url, params=None):
            calls.append(url)
            if params:
                self.assertIn("publicationTypeCode", params)
                self.assertIn("monographDoctoralThesis", params["publicationTypeCode"])
            if "resultList.jsf" in url:
                return result_page(ULF_URL)
            return record_page(query.title, "Andersson, Ulf", "University of Borås", 2023, "hb.diva-portal.org")

        with patch("app.providers.diva.fetch_text", side_effect=fake_fetch):
            candidates = diva.search(query)

        self.assertEqual(candidates[0]["source_host"], "hb.diva-portal.org")
        self.assertTrue(calls[0].startswith("https://hb.diva-portal.org/"))

    def test_hanna_maurin_soderholm_known_person_search_returns_hb_thesis(self):
        hanna_url = "https://hb.diva-portal.org/smash/record.jsf?pid=diva2%3A877048"
        title = "Emergency visualized : exploring visual technology for paramedic-physician collaboration in emergency care"
        query = SearchQuery(author="Hanna Maurin Söderholm")

        def fake_fetch(url, params=None):
            if "resultList.jsf" in url:
                if "hb.diva-portal.org" in url:
                    return result_page(hanna_url)
                return "<html><body></body></html>"
            return record_page(title, "Maurin Söderholm, Hanna", "Högskolan i Borås", 2015, "hb.diva-portal.org")

        with patch("app.providers.diva.fetch_text", side_effect=fake_fetch):
            candidates = diva.search_host("hb.diva-portal.org", query, 5)

        self.assertEqual(candidates[0]["dissertation_url"], hanna_url)
        self.assertEqual(candidates[0]["source_host"], "hb.diva-portal.org")
        self.assertEqual(candidates[0]["publication_type"], "dissertation")

    def test_result_urls_parse_when_pid_is_not_first_query_param(self):
        html = """
        <html><body>
          <a href="/smash/record.jsf?dswid=8008&amp;pid=diva2%3A877048&amp;c=14&amp;language=sv">
            Emergency visualized
          </a>
        </body></html>
        """

        urls = diva.find_record_urls(html, "hb.diva-portal.org")

        self.assertEqual(urls, ["https://hb.diva-portal.org/smash/record.jsf?pid=diva2%3A877048"])

    def test_result_page_prefilters_articles_before_record_fetch(self):
        html = """
        <ul>
          <li class="ui-datalist-item">
            <a href="/smash/record.jsf?pid=diva2%3A111">Journal article</a>
            <span>Article in journal (Refereed)</span>
          </li>
          <li class="ui-datalist-item">
            <a href="/smash/record.jsf?pid=diva2%3A432398">Akut omhändertagande</a>
            <span>Doctoral thesis, comprehensive summary</span>
          </li>
        </ul>
        """

        urls = diva.find_dissertation_record_urls(html, "lnu.diva-portal.org")

        self.assertEqual(
            urls,
            ["https://lnu.diva-portal.org/smash/record.jsf?pid=diva2%3A432398"],
        )

    def test_agnes_olander_search_uses_boras_diva_host_first(self):
        query = SearchQuery(
            title="När livet plötsligt tar en ny vändning. Att förstå, hantera och identifiera allvaret vid insjuknandet i sepsis.",
            author="Agnes Olander",
            university="Högskolan i Borås",
            year=2023,
        )

        def fake_fetch(url, params=None):
            if "resultList.jsf" in url:
                return result_page(AGNES_URL)
            return record_page(query.title, "Olander, Agnes", "University of Borås", 2023, "hb.diva-portal.org")

        with patch("app.providers.diva.fetch_text", side_effect=fake_fetch):
            candidates = diva.search(query)

        self.assertEqual(candidates[0]["source_host"], "hb.diva-portal.org")
        self.assertGreaterEqual(candidates[0]["confidence"], 0.9)

    def test_diva_candidate_penalizes_weaker_library_hit(self):
        result = apply_diva_preference(
            [
                {"source": "SwePub", "confidence": 0.96},
                {"source": "DiVA", "confidence": 0.9},
            ]
        )

        swepub = next(candidate for candidate in result if candidate["source"] == "SwePub")
        self.assertLessEqual(swepub["confidence"], 0.74)


if __name__ == "__main__":
    unittest.main()
