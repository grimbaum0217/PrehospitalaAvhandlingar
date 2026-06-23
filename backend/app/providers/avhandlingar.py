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
    normalize_candidate,
    normalize_year,
    score_candidate,
)


SOURCE = "avhandlingar.se"
BASE_URL = "https://www.avhandlingar.se"


def search(query: SearchQuery, limit: int = 5) -> list[dict]:
    if not query.as_text():
        return []

    html = fetch_text(search_url(query))
    urls = find_dissertation_urls(html)
    candidates = []
    for url in urls[:limit]:
        candidates.append(record_candidate(url, query))
    return candidates


def search_url(query: SearchQuery) -> str:
    slug = quote_plus(query.as_text()).replace("+", "_")
    return f"{BASE_URL}/om/{slug}/"


def find_dissertation_urls(html: str) -> list[str]:
    urls = []
    for href in re.findall(r'href=["\']([^"\']+)["\']', html):
        if "/avhandling/" not in href and "/dissertation/" not in href:
            continue
        url = absolute_url(BASE_URL, href.replace("&amp;", "&"))
        if url and url not in urls:
            urls.append(url)
    return urls


def record_candidate(record_url: str, query: SearchQuery) -> dict:
    html = fetch_text(record_url)
    meta = extract_meta(html).meta
    page_title = clean_text(meta.get("og:title") or meta.get("title") or "")
    title, author = split_title_author(page_title)

    candidate = normalize_candidate(
        {
            "title": title,
            "author": author,
            "university": extract_labeled_value(html, ["University", "Universitet"]),
            "year": extract_year(html),
            "dissertation_url": extract_repository_url(html) or record_url,
            "pdf_url": extract_pdf_url(html),
            "doi": find_doi(html),
            "abstract": clean_text(meta.get("description")),
        },
        SOURCE,
    )
    candidate["source_url"] = candidate.get("dissertation_url")
    candidate["source_host"] = source_host(candidate.get("dissertation_url"))
    candidate["confidence"] = round(score_candidate(candidate, query), 3)
    return candidate


def split_title_author(page_title: str) -> tuple[str | None, str | None]:
    for separator in [" by ", " / ", " - "]:
        if separator in page_title:
            left, right = page_title.split(separator, 1)
            if separator == " by ":
                return clean_text(left) or None, clean_text(right) or None
            return clean_text(left) or None, clean_text(right) or None
    return page_title or None, None


def extract_labeled_value(html: str, labels: list[str]) -> str | None:
    for label in labels:
        pattern = rf"{re.escape(label)}\s*:?\s*</[^>]+>\s*<[^>]+>([^<]+)"
        match = re.search(pattern, html, flags=re.I)
        if match:
            return clean_text(match.group(1))
    return None


def extract_year(html: str) -> int | None:
    return normalize_year(extract_labeled_value(html, ["Year", "År"]) or html)


def extract_pdf_url(html: str) -> str | None:
    match = re.search(r'href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']', html, flags=re.I)
    if not match:
        return None
    return absolute_url(BASE_URL, match.group(1).replace("&amp;", "&"))


def extract_repository_url(html: str) -> str | None:
    repository_hosts = [
        "diva-portal.org",
        "openarchive.ki.se",
        "lup.lub.lu.se",
        "gupea.ub.gu.se",
    ]
    for href in re.findall(r'href=["\']([^"\']+)["\']', html):
        url = href.replace("&amp;", "&")
        if any(host in url for host in repository_hosts):
            return absolute_url(BASE_URL, url)
    return None


def source_host(url: str | None) -> str | None:
    if not url:
        return None
    match = re.match(r"https?://([^/]+)", url)
    return match.group(1).lower() if match else None
