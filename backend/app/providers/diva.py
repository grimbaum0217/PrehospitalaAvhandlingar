from __future__ import annotations

import re
import unicodedata
from urllib.parse import quote_plus, urlparse

from app.providers.common import (
    MetadataError,
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
PORTAL_HOST = "www.diva-portal.org"

UNIVERSITY_HOSTS = {
    "orebro universitet": ["oru.diva-portal.org"],
    "orebro university": ["oru.diva-portal.org"],
    "örebro universitet": ["oru.diva-portal.org"],
    "örebro university": ["oru.diva-portal.org"],
    "hogskolan i boras": ["hb.diva-portal.org"],
    "hogskolan boras": ["hb.diva-portal.org"],
    "högskolan i borås": ["hb.diva-portal.org"],
    "högskolan borås": ["hb.diva-portal.org"],
    "university of boras": ["hb.diva-portal.org"],
    "umea universitet": ["umu.diva-portal.org"],
    "umeå universitet": ["umu.diva-portal.org"],
    "umea university": ["umu.diva-portal.org"],
    "umeå university": ["umu.diva-portal.org"],
    "uppsala universitet": ["uu.diva-portal.org"],
    "uppsala university": ["uu.diva-portal.org"],
    "linkopings universitet": ["liu.diva-portal.org"],
    "linköpings universitet": ["liu.diva-portal.org"],
    "linkoping university": ["liu.diva-portal.org"],
    "linköping university": ["liu.diva-portal.org"],
    "lunds universitet": ["lup.lub.lu.se", "lu.diva-portal.org"],
    "lund university": ["lup.lub.lu.se", "lu.diva-portal.org"],
}


def search(query: SearchQuery, limit: int = 5) -> list[dict]:
    if not query.as_text():
        return []

    targeted_hosts = hosts_for_university(query.university)
    candidates = []
    errors = []

    for host in targeted_hosts:
        try:
            candidates.extend(search_host(host, query, limit))
        except MetadataError as exc:
            errors.append(exc)
        if has_strong_candidate(candidates):
            return deduplicate(candidates)[:limit]

    if not candidates:
        try:
            candidates.extend(search_host(PORTAL_HOST, query, limit))
        except MetadataError as exc:
            errors.append(exc)

    if not candidates and errors:
        raise errors[0]

    return deduplicate(candidates)[:limit]


def search_host(host: str, query: SearchQuery, limit: int) -> list[dict]:
    urls = []
    for search_text in search_texts(query):
        html = fetch_text(
            search_url(host),
            params={
                "query": search_text,
                "language": "en",
                "searchType": "SIMPLE",
                "noOfRows": limit,
                "sortOrder": "relevance_sort_desc",
            },
        )
        for url in find_record_urls(html, host):
            if url not in urls:
                urls.append(url)
        if urls:
            break

    candidates = []
    for record_url in urls[:limit]:
        candidate = record_candidate(record_url, query)
        if is_dissertation_candidate(candidate):
            candidates.append(candidate)
    return candidates


def search_texts(query: SearchQuery) -> list[str]:
    variants = [
        " ".join(clean_text(value) for value in [query.title, query.author, query.year] if clean_text(value)),
        " ".join(clean_text(value) for value in [query.title, query.author] if clean_text(value)),
        clean_text(query.title),
        " ".join(clean_text(value) for value in [query.author, query.year] if clean_text(value)),
        query.as_text(),
    ]
    return [variant for index, variant in enumerate(variants) if variant and variant not in variants[:index]]


def find_record_urls(html: str, host: str = PORTAL_HOST) -> list[str]:
    urls = []
    for href in re.findall(r'href=["\']([^"\']*record\.jsf\?pid=[^"\']+)["\']', html):
        url = absolute_url(f"https://{host}", href.replace("&amp;", "&"))
        if url and url not in urls:
            urls.append(url)
    return urls


def record_candidate(record_url: str, query: SearchQuery) -> dict:
    if not is_diva_record_url(record_url):
        raise MetadataError("URL is not a DiVA record")

    html = fetch_text(record_url)
    meta = extract_meta(html).meta
    host = urlparse(record_url).netloc

    pdf_url = first_value(
        meta,
        [
            "citation_pdf_url",
            "DC.identifier.fulltext",
            "dc.identifier.fulltext",
        ],
    )
    title = first_value(meta, ["citation_title", "DC.Title", "DC.title", "dc.title", "og:title"])
    author = first_value(meta, ["citation_author", "DC.Creator", "DC.creator", "dc.creator"])
    university = first_value(
        meta,
        [
            "citation_dissertation_institution",
            "DC.Publisher",
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
            "DC.Date",
            "dc.date",
            "citation_date",
        ],
    )
    abstract = first_value(
        meta,
        [
            "citation_abstract",
            "DC.Description",
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
            "pdf_url": absolute_url(f"https://{host}", pdf_url),
            "urn": first_value(meta, ["DC.Identifier.urn", "DC.identifier.urn", "dc.identifier.urn"])
            or find_urn(html),
            "doi": first_value(meta, ["citation_doi", "DC.identifier.doi", "dc.identifier.doi"])
            or find_doi(html),
            "source_host": host,
        },
        SOURCE,
    )
    if abstract:
        candidate["abstract"] = clean_text(abstract)
    candidate["confidence"] = round(score_candidate(candidate, query), 3)
    return candidate


def search_url_for_debug(query: SearchQuery) -> str:
    return f"{search_url(PORTAL_HOST)}?query={quote_plus(query.as_text())}"


def lookup_url(url: str, query: SearchQuery | None = None) -> dict:
    lookup_query = query or SearchQuery()
    return record_candidate(url, lookup_query)


def is_diva_record_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    return (
        parsed.path.endswith("/smash/record.jsf")
        and "pid=" in parsed.query
        and (
            host.endswith(".diva-portal.org")
            or host == PORTAL_HOST
            or host == "lup.lub.lu.se"
        )
    )


def search_url(host: str) -> str:
    return f"https://{host}/smash/resultList.jsf"


def hosts_for_university(university: str | None) -> list[str]:
    normalized = normalize_university(university)
    return UNIVERSITY_HOSTS.get(normalized, [])


def normalize_university(value: str | None) -> str:
    text = clean_text(value).lower()
    text = text.replace("&", " och ")
    ascii_text = "".join(
        char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-zåäö0-9]+", " ", ascii_text).strip()


def has_strong_candidate(candidates: list[dict]) -> bool:
    return any(candidate.get("confidence", 0) >= 0.82 for candidate in candidates)


def is_dissertation_candidate(candidate: dict) -> bool:
    title = clean_text(candidate.get("title")).lower()
    return bool(candidate.get("dissertation_url")) and bool(title)


def deduplicate(candidates: list[dict]) -> list[dict]:
    by_url = {}
    for candidate in candidates:
        key = candidate.get("urn") or candidate.get("dissertation_url")
        if not key:
            continue
        current = by_url.get(key)
        if current is None or candidate.get("confidence", 0) > current.get("confidence", 0):
            by_url[key] = candidate
    return sorted(by_url.values(), key=lambda candidate: candidate.get("confidence", 0), reverse=True)
