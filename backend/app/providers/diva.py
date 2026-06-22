from __future__ import annotations

import re
from urllib.parse import quote_plus

from app.providers.common import (
    SearchQuery,
    absolute_url,
    clean_text,
    extract_meta,
    fetch_text,
    find_doi,
    find_urn,
    first_value,
    normalize_candidate,
    score_candidate,
)


SOURCE = "DiVA"
BASE_URL = "https://www.diva-portal.org"
SEARCH_URL = f"{BASE_URL}/smash/resultList.jsf"


def search(query: SearchQuery, limit: int = 5) -> list[dict]:
    if not query.as_text():
        return []

    html = fetch_text(
        SEARCH_URL,
        params={
            "query": query.as_text(),
            "language": "en",
            "searchType": "SIMPLE",
            "noOfRows": limit,
            "sortOrder": "relevance_sort_desc",
        },
    )

    record_urls = find_record_urls(html)
    candidates = []
    for record_url in record_urls[:limit]:
        candidates.append(record_candidate(record_url, query))
    return candidates


def find_record_urls(html: str) -> list[str]:
    urls = []
    for href in re.findall(r'href=["\']([^"\']*record\.jsf\?pid=[^"\']+)["\']', html):
        url = absolute_url(BASE_URL, href.replace("&amp;", "&"))
        if url and url not in urls:
            urls.append(url)
    return urls


def record_candidate(record_url: str, query: SearchQuery) -> dict:
    html = fetch_text(record_url)
    meta = extract_meta(html).meta

    pdf_url = first_value(
        meta,
        [
            "citation_pdf_url",
            "DC.identifier.fulltext",
            "dc.identifier.fulltext",
        ],
    )
    title = first_value(meta, ["citation_title", "DC.title", "dc.title", "og:title"])
    author = first_value(meta, ["citation_author", "DC.creator", "dc.creator"])
    university = first_value(
        meta,
        [
            "citation_dissertation_institution",
            "DC.publisher",
            "dc.publisher",
            "citation_publisher",
        ],
    )
    year = first_value(
        meta,
        [
            "citation_publication_date",
            "DC.date",
            "dc.date",
            "citation_date",
        ],
    )
    abstract = first_value(
        meta,
        [
            "DC.description",
            "dc.description",
            "description",
            "DCTERMS.abstract",
            "dcterms.abstract",
        ],
    )

    candidate = normalize_candidate(
        {
            "title": clean_text(title),
            "author": clean_text(author),
            "university": clean_text(university),
            "year": year,
            "dissertation_url": record_url,
            "pdf_url": absolute_url(BASE_URL, pdf_url),
            "urn": find_urn(html),
            "doi": first_value(meta, ["citation_doi", "DC.identifier.doi", "dc.identifier.doi"])
            or find_doi(html),
        },
        SOURCE,
    )
    if abstract:
        candidate["abstract"] = clean_text(abstract)
    candidate["confidence"] = round(score_candidate(candidate, query), 3)
    return candidate


def search_url_for_debug(query: SearchQuery) -> str:
    return f"{SEARCH_URL}?query={quote_plus(query.as_text())}"
