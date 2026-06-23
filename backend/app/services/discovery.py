from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import DiscoveryCandidate, Thesis
from app.providers import SearchQuery
from app.providers import avhandlingar, diva, swepub
from app.providers.common import (
    MetadataError,
    clean_text,
    comparable_text,
    fetch_json,
    normalize_year,
    similarity,
)


SWEDISH_KEYWORDS = [
    "ambulanssjukvård",
    "prehospital",
    "prehospital akutsjukvård",
    "larmcentral",
    "ambulans",
    "akutsjukvård utanför sjukhus",
    "hjärtstopp utanför sjukhus",
    "skadeplats",
    "räddningstjänst",
    "ivpa",
]

ENGLISH_KEYWORDS = [
    "prehospital",
    "emergency medical services",
    "emergency care",
    "ems",
    "ambulance",
    "paramedic",
    "out-of-hospital",
    "emergency dispatch",
    "out-of-hospital cardiac arrest",
    "ohca",
    "first responder",
]

KEYWORD_GROUPS = {
    "all": SWEDISH_KEYWORDS + ENGLISH_KEYWORDS,
    "swedish": SWEDISH_KEYWORDS,
    "english": ENGLISH_KEYWORDS,
}

DISCOVERY_SOURCES = ["diva", "avhandlingar", "swepub", "libris"]
LIBRIS_SEARCH_URL = "https://libris.kb.se/xsearch"
LIBRARY_SOURCES = {"LIBRIS", "SwePub"}
REPOSITORY_HOSTS = ("diva-portal.org", "openarchive.ki.se", "lup.lub.lu.se", "gupea.ub.gu.se")


def discover_candidates(db: Session, params: dict[str, Any]) -> dict[str, Any]:
    year_from = normalize_year(params.get("year_from")) or 2024
    year_to = normalize_year(params.get("year_to"))
    source = params.get("source") or "all"
    keyword_group = params.get("keyword_group") or "all"
    known_person = clean_text(params.get("known_person"))
    university = clean_text(params.get("university"))
    include_known = bool(params.get("show_known_matches"))
    limit_per_query = int(params.get("limit_per_query") or 8)

    keywords = KEYWORD_GROUPS.get(keyword_group, KEYWORD_GROUPS["all"])
    search_terms = [known_person] if known_person else keywords
    sources = DISCOVERY_SOURCES if source == "all" else [source]

    discovered = []
    errors = []
    stored = 0
    skipped_known = 0
    existing_theses = db.query(Thesis).all()

    for source_name in sources:
        for term in search_terms:
            try:
                records = search_source(source_name, term, known_person, university, limit_per_query)
            except MetadataError as exc:
                errors.append({"source": source_name, "term": term, "error": str(exc)})
                continue

            for record in records:
                if not in_year_range(record, year_from, year_to):
                    continue
                if not is_likely_dissertation_record(record):
                    continue

                matched_keywords = match_ems_keywords(record, keywords)
                if not matched_keywords:
                    continue

                duplicate = classify_duplicate(record, existing_theses)
                candidate = candidate_payload(record, matched_keywords, keyword_group, duplicate)
                discovered.append(candidate)

                if candidate["match_status"] == "already_in_database" and not include_known:
                    skipped_known += 1

                upsert_discovery_candidate(db, candidate)
                stored += 1

    db.commit()
    return {
        "stored": stored,
        "discovered": len(discovered),
        "skipped_known": skipped_known,
        "errors": errors,
    }


def search_source(
    source_name: str,
    term: str,
    known_person: str,
    university: str,
    limit: int,
) -> list[dict[str, Any]]:
    query = SearchQuery(
        title=term if not known_person else None,
        author=known_person or None,
        university=university or None,
    )
    if source_name == "diva":
        return search_diva_hosts(query, limit)
    if source_name == "swepub":
        return swepub.search(SearchQuery(title=term, author=known_person or None, university=university or None), limit=limit)
    if source_name == "libris":
        return search_libris(term, known_person, limit)
    if source_name == "avhandlingar":
        return avhandlingar.search(SearchQuery(title=term, author=known_person or None, university=university or None), limit=limit)
    return []


def search_diva_hosts(query: SearchQuery, limit: int) -> list[dict[str, Any]]:
    hosts = diva.hosts_for_university(query.university)
    if not hosts:
        hosts = []
        for mapped_hosts in diva.UNIVERSITY_HOSTS.values():
            for host in mapped_hosts:
                if host.endswith(".diva-portal.org") and host not in hosts:
                    hosts.append(host)

    results = []
    seen = set()
    for host in hosts:
        try:
            for candidate in diva.search_host(host, query, limit):
                key = candidate.get("urn") or candidate.get("dissertation_url")
                if key and key not in seen:
                    seen.add(key)
                    results.append(candidate)
        except MetadataError:
            continue
    return results


def search_libris(term: str, known_person: str, limit: int) -> list[dict[str, Any]]:
    query_text = " ".join(part for part in [term, known_person] if part)
    data = fetch_json(
        LIBRIS_SEARCH_URL,
        params={
            "query": query_text,
            "format": "json",
            "n": limit,
        },
    )
    records = data.get("xsearch", {}).get("list", [])
    candidates = []
    for record in records:
        candidate = swepub.record_candidate(record, SearchQuery(title=term, author=known_person))
        candidate["source"] = "LIBRIS"
        candidates.append(candidate)
    return candidates


def in_year_range(record: dict[str, Any], year_from: int | None, year_to: int | None) -> bool:
    year = normalize_year(record.get("year"))
    if year_from and (not year or year < year_from):
        return False
    if year_to and (not year or year > year_to):
        return False
    return True


def match_ems_keywords(record: dict[str, Any], keywords: list[str]) -> list[str]:
    haystack = " ".join(
        clean_text(record.get(field)).lower()
        for field in ["title", "keywords", "subject_terms"]
    )
    return [keyword for keyword in keywords if keyword.lower() in haystack]


def is_likely_dissertation_record(record: dict[str, Any]) -> bool:
    haystack = " ".join(
        clean_text(record.get(field)).lower()
        for field in ["title", "source", "document_type", "publication_type", "degree_type"]
    )
    if any(marker in haystack for marker in ["article", "journal", "tidskriftsartikel"]):
        return False
    if record.get("source") in LIBRARY_SOURCES and not any(
        marker in haystack for marker in ["dissertation", "thesis", "avhandling"]
    ):
        return False
    return bool(clean_text(record.get("title"))) and (
        any(marker in haystack for marker in ["dissertation", "thesis", "avhandling"])
        or bool(record.get("urn"))
        or bool(record.get("dissertation_url"))
    )


def classify_duplicate(record: dict[str, Any], theses: list[Thesis]) -> dict[str, Any]:
    best = {
        "match_status": "new_candidate",
        "similarity_to_existing": 0.0,
        "matched_existing_thesis_id": None,
        "matched_existing_running_number": None,
    }

    for thesis in theses:
        identifier_match = exact_identifier_match(record, thesis)
        title_score = similarity(record.get("title"), thesis.title)
        author_score = author_similarity(record.get("author"), thesis.author)
        university_score = similarity(record.get("university"), thesis.university)
        year_match = normalize_year(record.get("year")) == normalize_year(thesis.year)
        year_close = years_are_close(record.get("year"), thesis.year)
        combined = (
            title_score * 0.5
            + author_score * 0.28
            + (0.14 if year_match else 0.06 if year_close else 0)
            + university_score * 0.08
        )

        if identifier_match:
            combined = max(combined, 0.98)

        if combined > best["similarity_to_existing"]:
            best.update(
                {
                    "similarity_to_existing": round(combined, 3),
                    "matched_existing_thesis_id": thesis.id,
                    "matched_existing_running_number": thesis.running_number,
                }
            )

        if identifier_match or (
            title_score >= 0.9
            and author_score >= 0.82
            and (year_match or university_score >= 0.72)
        ):
            best["match_status"] = "already_in_database"
            best["similarity_to_existing"] = round(max(combined, 0.98), 3)
            best["matched_existing_thesis_id"] = thesis.id
            best["matched_existing_running_number"] = thesis.running_number
            return best

        possible_duplicate = (
            title_score >= 0.75
            or (author_score >= 0.85 and year_match)
            or (author_score >= 0.78 and year_close and university_score >= 0.7)
        )
        if possible_duplicate and best["match_status"] != "already_in_database":
            best["match_status"] = "possible_duplicate"

    return best


def author_similarity(left: Any, right: Any) -> float:
    left_parts = author_name_parts(left)
    right_parts = author_name_parts(right)
    if not left_parts or not right_parts:
        return 0.0

    base = similarity(" ".join(left_parts), " ".join(right_parts))
    left_set = set(left_parts)
    right_set = set(right_parts)
    overlap = len(left_set & right_set) / max(len(left_set), len(right_set))
    left_last = left_parts[-1]
    right_last = right_parts[-1]
    last_name_score = 1.0 if left_last == right_last else similarity(left_last, right_last)
    return max(base, overlap, last_name_score * 0.72)


def author_name_parts(value: Any) -> list[str]:
    text = comparable_text(value)
    if not text:
        return []
    if "," in clean_text(value):
        parts = [part.strip() for part in comparable_text(value).split() if part.strip()]
        return parts[1:] + parts[:1] if len(parts) > 1 else parts
    return text.split()


def years_are_close(left: Any, right: Any) -> bool:
    left_year = normalize_year(left)
    right_year = normalize_year(right)
    return bool(left_year and right_year and abs(left_year - right_year) <= 1)


def exact_identifier_match(record: dict[str, Any], thesis: Thesis) -> bool:
    for field in ["doi", "urn"]:
        left = clean_text(record.get(field)).lower()
        right = clean_text(getattr(thesis, field, None)).lower()
        if left and right and left == right:
            return True

    source_url = clean_text(record.get("dissertation_url")).lower()
    return bool(
        source_url
        and source_url
        in {
            clean_text(thesis.dissertation_url).lower(),
            clean_text(thesis.pdf_url).lower(),
        }
    )


def candidate_payload(
    record: dict[str, Any],
    matched_keywords: list[str],
    keyword_group: str,
    duplicate: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "title": clean_text(record.get("title")),
        "author": clean_text(record.get("author")) or None,
        "university": clean_text(record.get("university")) or None,
        "year": normalize_year(record.get("year")),
        "abstract": None,
        "source": record.get("source"),
        "source_host": record.get("source_host"),
        "source_url": record.get("source_url") or record.get("dissertation_url"),
        "pdf_url": record.get("pdf_url"),
        "publication_type": record.get("publication_type"),
        "doi": record.get("doi"),
        "urn": record.get("urn"),
        "matched_keywords": matched_keywords,
        "keyword_group": keyword_group,
        "review_status": "needs_review",
    }
    payload.update(duplicate)
    return payload


def upsert_discovery_candidate(db: Session, payload: dict[str, Any]) -> DiscoveryCandidate:
    existing = find_existing_candidate(db, payload)
    now = datetime.now(timezone.utc)
    candidate = existing or DiscoveryCandidate(created_at=now)

    for field in [
        "title",
        "author",
        "university",
        "year",
        "abstract",
        "source",
        "source_host",
        "source_url",
        "pdf_url",
        "publication_type",
        "doi",
        "urn",
        "keyword_group",
        "match_status",
        "similarity_to_existing",
        "matched_existing_thesis_id",
        "matched_existing_running_number",
    ]:
        if (
            existing
            and field in {"source", "source_host", "source_url", "pdf_url", "publication_type"}
            and not should_replace_source(existing, payload)
        ):
            continue
        setattr(candidate, field, payload.get(field))

    candidate.matched_keywords = json.dumps(payload.get("matched_keywords") or [], ensure_ascii=False)
    candidate.review_status = existing.review_status if existing else payload["review_status"]
    candidate.updated_at = now
    db.add(candidate)
    return candidate


def should_replace_source(existing: DiscoveryCandidate, payload: dict[str, Any]) -> bool:
    return source_rank(payload.get("source"), payload.get("source_host")) >= source_rank(
        existing.source,
        existing.source_host,
    )


def source_rank(source: str | None, source_host: str | None) -> int:
    if source == "DiVA":
        return 5
    if source_host and any(host in source_host for host in REPOSITORY_HOSTS):
        return 4
    if source == "avhandlingar.se":
        return 3
    if source == "SwePub":
        return 2
    if source == "LIBRIS":
        return 1
    return 0


def find_existing_candidate(db: Session, payload: dict[str, Any]) -> DiscoveryCandidate | None:
    clauses = []
    for field in ["doi", "urn", "source_url"]:
        value = payload.get(field)
        if value:
            clauses.append(getattr(DiscoveryCandidate, field) == value)
    if not clauses and payload.get("title"):
        clauses.append(DiscoveryCandidate.title == payload["title"])
    if not clauses:
        return None
    return db.query(DiscoveryCandidate).filter(or_(*clauses)).first()


def list_discovery_candidates(db: Session, params: dict[str, Any]) -> list[DiscoveryCandidate]:
    query = db.query(DiscoveryCandidate)
    match_status = params.get("match_status")
    review_status = params.get("review_status")
    include_known = bool(params.get("include_known"))

    if match_status and match_status != "all":
        query = query.filter(DiscoveryCandidate.match_status == match_status)
    elif not include_known:
        query = query.filter(DiscoveryCandidate.match_status != "already_in_database")
    if review_status and review_status != "all":
        query = query.filter(DiscoveryCandidate.review_status == review_status)

    return query.order_by(
        DiscoveryCandidate.year.desc(),
        DiscoveryCandidate.similarity_to_existing.desc(),
        DiscoveryCandidate.id.desc(),
    ).all()


def discovery_summary(db: Session) -> dict[str, Any]:
    total_theses = db.query(Thesis).count()
    awaiting_review = (
        db.query(DiscoveryCandidate)
        .filter(DiscoveryCandidate.match_status != "already_in_database")
        .filter(DiscoveryCandidate.review_status == "needs_review")
        .count()
    )
    approved = (
        db.query(DiscoveryCandidate)
        .filter(DiscoveryCandidate.match_status != "already_in_database")
        .filter(DiscoveryCandidate.review_status == "approved")
        .count()
    )
    rejected = (
        db.query(DiscoveryCandidate)
        .filter(DiscoveryCandidate.review_status == "rejected")
        .count()
    )
    possible_duplicates = (
        db.query(DiscoveryCandidate)
        .filter(DiscoveryCandidate.match_status == "possible_duplicate")
        .count()
    )
    return {
        "existing_theses": total_theses,
        "awaiting_review": awaiting_review,
        "approved_new_theses": approved,
        "rejected_candidates": rejected,
        "possible_duplicates": possible_duplicates,
    }


def serialize_discovery_candidate(candidate: DiscoveryCandidate) -> dict[str, Any]:
    return {
        "id": candidate.id,
        "title": candidate.title,
        "author": candidate.author,
        "university": candidate.university,
        "year": candidate.year,
        "abstract": candidate.abstract,
        "source": candidate.source,
        "source_host": candidate.source_host,
        "source_url": candidate.source_url,
        "pdf_url": candidate.pdf_url,
        "publication_type": candidate.publication_type,
        "doi": candidate.doi,
        "urn": candidate.urn,
        "matched_keywords": json.loads(candidate.matched_keywords or "[]"),
        "ems_match_reason": ems_match_reason(candidate),
        "keyword_group": candidate.keyword_group,
        "match_status": candidate.match_status,
        "similarity_to_existing": candidate.similarity_to_existing,
        "matched_existing_thesis_id": candidate.matched_existing_thesis_id,
        "matched_existing_running_number": candidate.matched_existing_running_number,
        "review_status": candidate.review_status,
        "created_at": candidate.created_at,
        "updated_at": candidate.updated_at,
    }


def ems_match_reason(candidate: DiscoveryCandidate) -> str:
    keywords = json.loads(candidate.matched_keywords or "[]")
    if keywords:
        return f"Matched EMS/prehospital keyword(s): {', '.join(keywords)}."
    return "Matched EMS/prehospital search criteria."
