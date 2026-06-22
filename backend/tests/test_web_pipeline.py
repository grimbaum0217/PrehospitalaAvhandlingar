import unittest
from unittest.mock import patch

from app.providers.common import SearchQuery
from app.services.web_pipeline import generate_search_queries, parse_candidate_url


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

    def test_journal_article_is_rejected(self):
        query = SearchQuery(title="Ambulance care in Sweden", author="Jane Doe", year=2024)

        with patch(
            "app.services.web_pipeline.fetch_text",
            return_value=page("Ambulance care in Sweden", document_type="journal article"),
        ):
            candidate = parse_candidate_url("https://example.org/article", query)

        self.assertEqual(candidate["classification"], "journal_article")
        self.assertEqual(candidate["confidence"], 0)


if __name__ == "__main__":
    unittest.main()
