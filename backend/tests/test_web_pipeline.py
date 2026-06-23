import unittest
from unittest.mock import patch

from app.providers.common import SearchQuery
from app.providers.common import MetadataError
from app.services.web_pipeline import (
    detect_platform,
    generate_search_queries,
    public_errors,
    repository_search_candidates,
    repository_search_urls,
    summarize_errors,
    parse_candidate_url,
)


def page(title, author="Doe, Jane", year=2024, document_type="doctoral thesis", pdf=True):
    pdf_meta = '<meta name="citation_pdf_url" content="/fulltext.pdf">' if pdf else ""
    return f"""
    <html>
      <head>
        <title>{title}</title>
        <meta name="citation_title" content="{title}">
        <meta name="citation_author" content="{author}">
        <meta name="citation_publication_date" content="{year}">
        <meta name="DC.Type" content="{document_type}">
        <meta name="DC.Description" content="A long abstract about ambulance care.">
        {pdf_meta}
      </head>
      <body>{document_type}</body>
    </html>
    """


class WebPipelineTests(unittest.TestCase):
    def test_generates_repository_queries(self):
        query = SearchQuery(
            title="Ambulance care in Sweden",
            author="Jane Doe",
            university="Uppsala Universitet",
            year=2024,
        )

        queries = generate_search_queries(query)

        self.assertIn('"Ambulance care in Sweden"', queries)
        self.assertIn("Jane Doe Uppsala Universitet 2024 avhandling", queries)
        self.assertIn("Ambulance care in Sweden site:openarchive.ki.se", queries)
        self.assertIn("Ambulance care in Sweden site:kth.diva-portal.org", queries)

    def test_repository_page_with_pdf_beats_library_record(self):
        query = SearchQuery(title="Ambulance care in Sweden", author="Jane Doe", year=2024)

        with patch("app.services.web_pipeline.fetch_text", return_value=page("Ambulance care in Sweden")):
            repo = parse_candidate_url("https://uu.diva-portal.org/smash/record.jsf?pid=diva2:1", query)
            library = parse_candidate_url("https://libris.kb.se/bib/example", query, "LIBRIS")

        self.assertEqual(repo["classification"], "dissertation_page")
        self.assertEqual(library["classification"], "library_record")
        self.assertGreater(repo["confidence"], library["confidence"])

    def test_manual_url_parser_reports_platform_and_missing_fields(self):
        query = SearchQuery(title="Ambulance care in Sweden", author="Jane Doe", year=2024)

        with patch("app.services.web_pipeline.fetch_text", return_value=page("Ambulance care in Sweden", pdf=False)):
            candidate = parse_candidate_url("https://openarchive.ki.se/articles/thesis/example", query)

        self.assertEqual(candidate["parser_used"], "ki_figshare_parser")
        self.assertIn("pdf_url", candidate["missing_fields"])
        self.assertEqual(candidate["parsed_fields"]["title"], "Ambulance care in Sweden")
        self.assertGreater(candidate["extraction_confidence"], 0)

    def test_platform_detector_covers_manual_import_sources(self):
        self.assertEqual(detect_platform("https://www.diva-portal.org/smash/record.jsf?pid=x"), "diva")
        self.assertEqual(detect_platform("https://openarchive.ki.se/articles/thesis/example"), "ki_figshare")
        self.assertEqual(detect_platform("https://lup.lub.lu.se/search/publication/example"), "lup")
        self.assertEqual(detect_platform("https://gupea.ub.gu.se/handle/2077/1"), "gupea")
        self.assertEqual(detect_platform("https://swepub.kb.se/bib/swepub:oai:example"), "swepub")
        self.assertEqual(detect_platform("https://libris.kb.se/bib/example"), "libris")

    def test_journal_article_is_rejected(self):
        query = SearchQuery(title="Ambulance care in Sweden", author="Jane Doe", year=2024)

        with patch(
            "app.services.web_pipeline.fetch_text",
            return_value=page("Ambulance care in Sweden", document_type="journal article"),
        ):
            candidate = parse_candidate_url("https://example.org/article", query)

        self.assertEqual(candidate["classification"], "journal_article")
        self.assertEqual(candidate["confidence"], 0)

    def test_repository_search_urls_only_use_known_endpoints(self):
        urls = repository_search_urls(SearchQuery(title="Ambulance care in Sweden"))

        self.assertEqual(len(urls), 2)
        self.assertTrue(all("/search?" in url or "simple-search" in url for url in urls))
        self.assertFalse(any("hb.diva-portal.org/search" in url for url in urls))

    def test_quiet_repository_errors_are_summarized_not_public(self):
        errors = [
            {"source": "repository_search", "url": "https://example.test/search", "error": "HTTP Error 404", "quiet": True},
            {"source": "DiVA", "error": "timeout"},
        ]

        self.assertEqual(public_errors(errors), [{"source": "DiVA", "error": "timeout"}])
        self.assertEqual(summarize_errors(errors)["count"], 1)

    def test_repository_search_404_returns_no_candidates(self):
        with patch(
            "app.services.web_pipeline.fetch_text",
            side_effect=MetadataError("HTTP Error 404: Not Found"),
        ):
            self.assertEqual(repository_search_candidates("https://example.test/search?q=x"), [])


if __name__ == "__main__":
    unittest.main()
