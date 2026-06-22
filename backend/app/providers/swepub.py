from __future__ import annotations

from typing import Any

from app.providers.common import (
    SearchQuery,
    clean_text,
    fetch_json,
    find_doi,
    normalize_candidate,
    score_candidate,
)


SOURCE = "SwePub"
SEARCH_URL = "https://libris.kb.se/xsearch"


def search(query: SearchQuery, limit: int = 8) -> list[dict]:
    if not query.as_text():
        return []

    # SwePub records are exposed through KB infrastructure. The LIBRIS xsearch
    # endpoint is intentionally used as a conservative public search surface here;
    # the provider filters and scores results locally before returning candidates.
    data = fetch_json(
        SEARCH_URL,
        params={
            "query": query.as_text(),
            "format": "json",
            "n": limit,
        },
    )
    records = data.get("xsearch", {}).get("list", [])

    candidates = []
    for record in records:
        candidate = record_candidate(record, query)
        if is_probable_dissertation(record, candidate, query):
            candidates.append(candidate)
    return candidates


def record_candidate(record: dict[str, Any], query: SearchQuery) -> dict:
    identifier = as_text(record.get("identifier"))
    date = first_list_value(record.get("date"))
    publisher = first_list_value(record.get("publisher"))
    candidate = normalize_candidate(
        {
            "title": as_text(record.get("title")),
            "author": as_text(record.get("creator")),
            "university": publisher,
            "year": date,
            "dissertation_url": identifier,
            "doi": find_doi(" ".join(as_text(value) for value in record.values())),
        },
        SOURCE,
    )
    candidate["confidence"] = round(score_candidate(candidate, query), 3)
    return candidate


def is_probable_dissertation(record: dict[str, Any], candidate: dict, query: SearchQuery) -> bool:
    haystack = " ".join(
        clean_text(value).lower()
        for value in [
            record.get("type"),
            record.get("genre"),
            record.get("title"),
            record.get("note"),
            candidate.get("title"),
        ]
    )
    dissertation_markers = [
        "doctoral",
        "dissertation",
        "thesis",
        "doktorsavhandling",
        "avhandling",
    ]
    if any(marker in haystack for marker in dissertation_markers):
        return True
    return candidate["confidence"] >= 0.82 and bool(query.title)


def as_text(value: Any) -> str:
    if isinstance(value, list):
        return clean_text(" ".join(as_text(item) for item in value))
    if isinstance(value, dict):
        return clean_text(" ".join(as_text(item) for item in value.values()))
    return clean_text(value)


def first_list_value(value: Any) -> str | None:
    if isinstance(value, list):
        return as_text(value[0]) if value else None
    return as_text(value) or None
