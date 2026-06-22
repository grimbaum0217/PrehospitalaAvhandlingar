from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, quote_plus, urlparse

from app.models import Thesis
from app.providers import SearchQuery
from app.providers import avhandlingar, diva, swepub
from app.providers.common import (
    MetadataError,
    absolute_url,
    clean_text,
    extract_meta,
    fetch_text,
    find_doi,
    find_urn,
    first_value,
    normalize_candidate,
    normalize_year,
    score_candidate,
    similarity,
)


REPOSITORY_HOSTS = [
    "diva-portal.org",
    "openarchive.ki.se",
    "hb.diva-portal.org",
    "oru.diva-portal.org",
    "lup.lub.lu.se",
    "gupea.ub.gu.se",
    "umu.diva-portal.org",
    "uu.diva-portal.org",
    "liu.diva-portal.org",
    "research.chalmers.se",
    "su.diva-portal.org",
    "kth.diva-portal.org",
]

RICH_REPOSITORY_HOSTS = [
    "diva-portal.org",
    "openarchive.ki.se",
    "gupea.ub.gu.se",
    "lup.lub.lu.se",
    "diva-portal.org",
    "research.chalmers.se",
]

LIBRARY_HOSTS = ["libris.kb.se", "swepub.kb.se"]
ARTICLE_MARKERS = ["journal article", "article", "tidskriftsartikel", "research article"]
THESIS_MARKERS = [
    "dissertation",
    "doctoral thesis",
    "doktorsavhandling",
    "thesis",
    "avhandling",
    "comprehensive summary",
]


class TitleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        if tag.lower() == "title":
            self.in_title = True

    def handle_endtag(self, tag: str):
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str):
        if self.in_title:
            self.title_parts.append(data)

    @property
    def title(self) -> str:
        return clean_text(" ".join(self.title_parts))


def lookup_thesis_web_candidates(thesis: Thesis) -> dict[str, Any]:
    query = SearchQuery(
        title=thesis.title,
        author=thesis.author,
        university=thesis.university,
        year=thesis.year,
    )
    url_candidates, errors = collect_candidate_urls(query)
    parsed_candidates = []

    for item in url_candidates:
        try:
            parsed = parse_candidate_url(item["url"], query, item.get("source"))
        except MetadataError as exc:
            errors.append({"source": item.get("source") or "web", "url": item["url"], "error": str(exc)})
            continue
        if parsed["classification"] not in {"irrelevant", "journal_article"}:
            parsed_candidates.append(parsed)

    candidates = deduplicate(parsed_candidates)
    candidates.sort(key=lambda candidate: candidate.get("confidence", 0), reverse=True)

    return {
        "search": {
            "title": thesis.title,
            "author": thesis.author,
            "university": thesis.university,
            "year": thesis.year,
            "queries": generate_search_queries(query),
        },
        "candidates": candidates,
        "errors": errors,
    }


def collect_candidate_urls(query: SearchQuery) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    candidates: list[dict[str, str]] = []
    errors = []

    for provider in [diva, swepub, avhandlingar]:
        try:
            for record in provider.search(query):
                url = record.get("dissertation_url") or record.get("pdf_url")
                if url:
                    candidates.append({"url": url, "source": record.get("source") or provider.SOURCE})
        except MetadataError as exc:
            errors.append({"source": provider.SOURCE, "error": str(exc)})

    for url in repository_search_urls(query):
        try:
            candidates.extend(repository_search_candidates(url))
        except MetadataError as exc:
            errors.append({"source": "repository_search", "url": url, "error": str(exc)})

    candidates.extend(generic_web_search_adapter(query))

    return deduplicate_urls(candidates), errors


def generate_search_queries(query: SearchQuery) -> list[str]:
    title = clean_text(query.title)
    author = clean_text(query.author)
    university = clean_text(query.university)
    year = clean_text(query.year)

    queries = [
        f'"{title}"',
        f'{author} "{title}"',
        f"{author} {university} {year} avhandling",
        f"{author} dissertation Sweden",
        f"{title} pdf",
    ]
    queries.extend(f"{title} site:{host}" for host in REPOSITORY_HOSTS)
    return [query_text for query_text in queries if clean_text(query_text)]


def repository_search_urls(query: SearchQuery) -> list[str]:
    title = quote_plus(clean_text(query.title))
    return [
        f"https://{host}/search?query={title}"
        for host in REPOSITORY_HOSTS
        if host not in {"diva-portal.org"}
    ]


def repository_search_candidates(search_url: str) -> list[dict[str, str]]:
    html = fetch_text(search_url)
    parsed = urlparse(search_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    parser = extract_meta(html)
    candidates = []
    for anchor in parser.anchors:
        href = anchor.get("href")
        if not href:
            continue
        url = absolute_url(base, href)
        if is_likely_record_url(url):
            candidates.append({"url": url, "source": "repository_search"})
    return candidates[:8]


def generic_web_search_adapter(query: SearchQuery) -> list[dict[str, str]]:
    # Placeholder for a future web search integration. It should return URLs only;
    # fetched pages still pass through this pipeline's parser, classifier, and ranker.
    return []


def is_likely_record_url(url: str | None) -> bool:
    if not url:
        return False
    lowered = url.lower()
    return any(
        marker in lowered
        for marker in [
            "record.jsf",
            "handle/",
            "/item/",
            "/publication/",
            "/en/publications/",
            ".pdf",
            "fulltext",
        ]
    )


def parse_candidate_url(url: str, query: SearchQuery, source_hint: str | None = None) -> dict[str, Any]:
    html = fetch_text(url)
    parsed_url = urlparse(url)
    host = parsed_url.netloc.lower()
    meta_parser = extract_meta(html)
    meta = meta_parser.meta
    html_title = parse_html_title(html)
    pdf_url = extract_pdf_url(url, html, meta, meta_parser.anchors)

    parsed_title = first_value(
        meta,
        ["citation_title", "DC.Title", "DC.title", "dc.title", "og:title", "title"],
    ) or html_title
    author = first_value(meta, ["citation_author", "DC.Creator", "DC.creator", "dc.creator"])
    university = first_value(
        meta,
        ["citation_publisher", "citation_dissertation_institution", "DC.Publisher", "dc.publisher"],
    )
    year = first_value(meta, ["citation_publication_date", "DC.date", "dc.date", "citation_date"])
    abstract = first_value(
        meta,
        ["citation_abstract", "DC.Description", "DC.description", "dc.description", "description"],
    )
    document_type = detect_document_type(html, meta, host)
    included_papers = extract_included_papers(html)

    candidate = normalize_candidate(
        {
            "title": parsed_title,
            "author": author,
            "university": university,
            "year": year,
            "dissertation_url": url,
            "pdf_url": pdf_url,
            "urn": first_value(meta, ["DC.Identifier.urn", "dc.identifier.urn"]) or find_urn(html),
            "doi": first_value(meta, ["citation_doi", "DC.identifier.doi", "dc.identifier.doi"])
            or find_doi(html),
            "abstract": abstract,
            "source": source_name(host, source_hint),
            "source_host": host,
        },
        source_name(host, source_hint),
    )
    classification = classify_candidate(candidate, document_type, html, host, query)
    candidate.update(
        {
            "html_title": html_title,
            "parsed_title": candidate.get("title"),
            "document_type": document_type,
            "classification": classification,
            "has_abstract": bool(candidate.get("abstract")),
            "has_pdf": bool(candidate.get("pdf_url")),
            "included_papers": included_papers,
            "confidence": rank_candidate(candidate, classification, host, query),
        }
    )
    return candidate


def parse_html_title(html: str) -> str:
    parser = TitleParser()
    parser.feed(html)
    return parser.title


def extract_pdf_url(page_url: str, html: str, meta: dict[str, str], anchors: list[dict[str, str]]) -> str | None:
    parsed = urlparse(page_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    pdf_url = first_value(meta, ["citation_pdf_url", "DC.identifier.fulltext", "dc.identifier.fulltext"])
    if pdf_url:
        return absolute_url(base, pdf_url)
    for anchor in anchors:
        href = anchor.get("href")
        label = clean_text(anchor.get("title") or anchor.get("aria-label")).lower()
        if href and (".pdf" in href.lower() or "fulltext" in href.lower() or "download" in label):
            return absolute_url(base, href)
    match = re.search(r'href=["\']([^"\']+(?:\.pdf|FULLTEXT|fulltext)[^"\']*)["\']', html, flags=re.I)
    if match:
        return absolute_url(base, match.group(1).replace("&amp;", "&"))
    return None


def detect_document_type(html: str, meta: dict[str, str], host: str) -> str:
    haystack = " ".join(
        clean_text(value).lower()
        for value in [
            *meta.values(),
            re.sub(r"<[^>]+>", " ", html[:20000]),
            host,
        ]
    )
    if any(marker in haystack for marker in ["doctoral thesis", "doktorsavhandling", "dissertation"]):
        return "doctoral_thesis"
    if "student thesis" in haystack or "master thesis" in haystack:
        return "student_thesis"
    if any(marker in haystack for marker in ARTICLE_MARKERS):
        return "journal_article"
    if "thesis" in haystack or "avhandling" in haystack:
        return "thesis_page"
    if any(host.endswith(library_host) for library_host in LIBRARY_HOSTS):
        return "library_record"
    return "unknown"


def classify_candidate(candidate: dict[str, Any], document_type: str, html: str, host: str, query: SearchQuery) -> str:
    title_score = similarity(query.title, candidate.get("title"))
    author_score = similarity(query.author, candidate.get("author"))
    repository = is_repository_host(host)
    library = is_library_host(host)
    if document_type == "journal_article":
        return "journal_article"
    if library:
        return "library_record"
    if title_score < 0.55 and author_score < 0.55:
        return "irrelevant"
    if document_type in {"doctoral_thesis", "thesis_page"} and repository:
        return "dissertation_page"
    if document_type in {"doctoral_thesis", "thesis_page"}:
        return "dissertation_page"
    if candidate.get("pdf_url") and title_score >= 0.8:
        return "dissertation_page"
    return "irrelevant"


def rank_candidate(candidate: dict[str, Any], classification: str, host: str, query: SearchQuery) -> float:
    base = score_candidate(candidate, query)
    repository = is_repository_host(host)
    library = is_library_host(host)
    if classification == "dissertation_page" and repository:
        base += 0.25
    elif classification == "dissertation_page":
        base += 0.15
    elif classification == "library_record":
        base += 0.03
    if candidate.get("abstract"):
        base += 0.08
    if candidate.get("pdf_url"):
        base += 0.08
    if repository:
        base += 0.06
    if library:
        base -= 0.12
    if similarity(query.title, candidate.get("title")) >= 0.92:
        base += 0.12
    if library:
        base = min(base, 0.74)
    if classification in {"journal_article", "irrelevant"}:
        base = 0
    return round(max(0, min(base, 1.0)), 3)


def is_repository_host(host: str) -> bool:
    return any(repository_host in host for repository_host in RICH_REPOSITORY_HOSTS)


def is_library_host(host: str) -> bool:
    return any(host.endswith(library_host) for library_host in LIBRARY_HOSTS)


def source_name(host: str, source_hint: str | None) -> str:
    if source_hint and source_hint != "repository_search":
        return source_hint
    if "diva-portal.org" in host:
        return "DiVA"
    if "openarchive.ki.se" in host:
        return "KI Open Archive"
    if "gupea.ub.gu.se" in host:
        return "GUPEA"
    if "lup.lub.lu.se" in host:
        return "LUP"
    if "libris.kb.se" in host:
        return "LIBRIS"
    if "swepub.kb.se" in host:
        return "SwePub"
    return host


def extract_included_papers(html: str) -> list[dict[str, str]]:
    text = re.sub(r"<[^>]+>", "\n", html)
    lines = [clean_text(line) for line in text.splitlines() if clean_text(line)]
    papers = []
    for line in lines:
        if find_doi(line) and len(line) > 40:
            papers.append({"title": line[:500], "doi": find_doi(line)})
        if len(papers) >= 8:
            break
    return papers


def deduplicate(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for candidate in candidates:
        key = candidate_key(candidate)
        current = by_key.get(key)
        if current is None or candidate.get("confidence", 0) > current.get("confidence", 0):
            by_key[key] = candidate
    return list(by_key.values())


def deduplicate_urls(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    unique = []
    for item in items:
        url = normalize_url(item["url"])
        if url not in seen:
            seen.add(url)
            unique.append({"url": url, "source": item.get("source")})
    return unique


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.endswith("diva-portal.org"):
        qs = parse_qs(parsed.query)
        pid = qs.get("pid", [None])[0]
        if pid:
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?pid={pid}"
    return url


def candidate_key(candidate: dict[str, Any]) -> tuple[str, str]:
    for field in ["doi", "urn", "pdf_url", "dissertation_url"]:
        if candidate.get(field):
            return field, candidate[field].lower()
    return "title", clean_text(candidate.get("title")).lower()
