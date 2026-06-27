from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_
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
    "pre-hospital care",
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

DISCOVERY_SOURCES = ["avhandlingar", "diva", "swepub", "libris"]
LIBRIS_SEARCH_URL = "https://libris.kb.se/xsearch"
LIBRARY_SOURCES = {"LIBRIS", "SwePub"}
REPOSITORY_HOSTS = ("diva-portal.org", "openarchive.ki.se", "lup.lub.lu.se", "gupea.ub.gu.se")
logger = logging.getLogger(__name__)


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
    direct_url = diva.direct_record_url(known_person)
    search_terms = [known_person] if known_person else keywords
    sources = ["diva_direct"] if direct_url else DISCOVERY_SOURCES if source == "all" else [source]

    discovered = []
    errors = []
    stored = 0
    skipped_known = 0
    existing_theses = db.query(Thesis).all()
    logger.info(
        "[discovery] search "
        f"known_person={known_person!r} normalized={person_name_from_known_person_input(known_person)!r} "
        f"source={source} year_from={year_from} year_to={year_to} limit={limit_per_query}"
    )

    if known_person and diva.looks_like_direct_reference(known_person) and not direct_url:
        return {
            "stored": 0,
            "discovered": 0,
            "skipped_known": 0,
            "candidates": [],
            "errors": [
                {
                    "source": "DiVA",
                    "term": known_person,
                    "code": "invalid_direct_reference",
                    "error": "Invalid DiVA URL or identifier",
                }
            ],
        }

    for source_name in sources:
        accepted_from_source = 0
        for term in search_terms:
            try:
                records = search_source(
                    source_name,
                    direct_url or term,
                    "" if direct_url else known_person,
                    university,
                    limit_per_query,
                )
            except MetadataError as exc:
                error = provider_error(source_name, term, exc)
                logger.warning(
                    "[discovery] provider_failed source=%s variant=%r code=%s reason=%s",
                    source_name,
                    term,
                    error["code"],
                    error["error"],
                )
                errors.append(error)
                continue
            except Exception as exc:
                logger.exception(
                    "[discovery] source_failed source=%s term=%r",
                    source_name,
                    term,
                )
                errors.append({"source": source_name, "term": term, "error": str(exc)})
                continue

            for record in records:
                if (
                    not known_person
                    and not in_year_range(
                        record,
                        year_from,
                        year_to,
                        allow_missing_year=source_name == "avhandlingar",
                    )
                ):
                    log_filter_drop(record, "year_out_of_range")
                    continue
                if not is_likely_dissertation_record(record):
                    log_filter_drop(record, "not_dissertation")
                    continue
                if known_person and not direct_url and not known_person_matches_record(known_person, record):
                    log_filter_drop(record, "author_mismatch")
                    continue

                matched_keywords = match_ems_keywords(record, keywords)
                if not matched_keywords and not known_person:
                    log_filter_drop(record, "missing_prehospital_keywords")
                    continue

                duplicate = classify_duplicate(record, existing_theses)
                candidate = candidate_payload(record, matched_keywords, keyword_group, duplicate)
                discovered.append(candidate)

                if candidate["match_status"] == "already_in_database" and not include_known:
                    skipped_known += 1

                upsert_discovery_candidate(db, candidate)
                stored += 1
                accepted_from_source += 1
                logger.info(
                    "[discovery] accepted "
                    f"pid={diva.pid_from_url(candidate.get('source_url'))} "
                    f"title={candidate.get('title')!r} status={candidate.get('match_status')}"
                )

        if known_person and source == "all" and source_name == "avhandlingar" and accepted_from_source:
            break

    db.commit()
    logger.info(
        "[discovery] final_candidates=%s stored=%s skipped_known=%s",
        len(discovered),
        stored,
        skipped_known,
    )
    return {
        "stored": stored,
        "discovered": len(discovered),
        "skipped_known": skipped_known,
        "candidates": normalized_discovery_results(discovered),
        "errors": errors,
    }


def search_source(
    source_name: str,
    term: str,
    known_person: str,
    university: str,
    limit: int,
) -> list[dict[str, Any]]:
    if source_name == "diva_direct":
        return [diva.lookup_url(term, SearchQuery())]
    if known_person:
        return search_known_person_source(source_name, known_person, university, limit)

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


def provider_error(source: str, term: str, exc: Exception) -> dict[str, str]:
    message = clean_text(exc)
    lowered = message.lower()
    code = "timeout" if "timed out" in lowered or "timeout" in lowered else "provider_error"
    status_match = re.search(r"http error\s+(\d{3})", message, flags=re.I)
    error = {"source": source, "term": term, "code": code, "error": message}
    if status_match:
        error["status_code"] = status_match.group(1)
    return error


def search_known_person_source(
    source_name: str,
    known_person: str,
    university: str,
    limit: int,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen = set()
    person_name = person_name_from_known_person_input(known_person)
    for variant in known_person_query_variants(person_name):
        query = SearchQuery(author=variant, university=university or None)
        if source_name == "avhandlingar":
            variant_records = avhandlingar.search(query, limit=limit)
        elif source_name == "diva":
            variant_records = search_diva_hosts(query, limit)
        elif source_name == "swepub":
            variant_records = swepub.search(query, limit=limit)
        elif source_name == "libris":
            variant_records = search_libris("", variant, limit)
        else:
            variant_records = []

        for record in variant_records:
            key = (
                record.get("urn")
                or record.get("doi")
                or record.get("source_url")
                or record.get("dissertation_url")
                or record.get("title")
            )
            if key and key not in seen:
                seen.add(key)
                records.append(record)
        if source_name in {"avhandlingar", "diva"} and records:
            return records
    return records


def known_person_query_variants(name: str) -> list[str]:
    tokens = person_tokens_for_query(name)
    if not tokens:
        return []

    search_name = " ".join(tokens)
    variants = [search_name]
    if len(tokens) >= 2:
        given = tokens[0]
        family = " ".join(tokens[1:])
        variants.append(f'"{search_name}"')
        variants.append(f"{given} {tokens[-1]}")
        variants.append(f"{family} {given}")
        variants.append(f"{family}, {given}")
        variants.append(f"{given} AND {family}")
        variants.append(family)
        if len(tokens[-1]) == 1:
            variants.append(f"{given} {tokens[-1]}*")
        if len(given) == 1:
            variants.append(f"{given}* {family}")
        variants.extend(last_name_query_variants(tokens))
        if family:
            variants.append(f'"{family}"')
    return unique_texts(variants)


def person_tokens_for_query(name: str) -> list[str]:
    raw = clean_text(name)
    if "," in raw:
        family, given = raw.split(",", 1)
        reordered = f"{given.strip()} {family.strip()}"
        return person_name_from_known_person_input(reordered).split()
    return person_name_from_known_person_input(raw).split()


def last_name_query_variants(tokens: list[str]) -> list[str]:
    last = tokens[-1]
    surname_combo = " ".join(tokens[1:]) if len(tokens) > 2 else last
    return [
        f"{last} thesis",
        f"{last} dissertation",
        f"{last} avhandling",
        f"{surname_combo} thesis",
        f"{surname_combo} dissertation",
        f"{surname_combo} avhandling",
    ]


def unique_texts(values: list[str]) -> list[str]:
    seen = set()
    unique = []
    for value in values:
        cleaned = clean_text(value)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            unique.append(cleaned)
    return unique


def search_diva_hosts(query: SearchQuery, limit: int) -> list[dict[str, Any]]:
    hosts = diva.hosts_for_university(query.university)
    if not hosts:
        hosts = diva.all_known_hosts()

    results = []
    seen = set()
    for host in hosts:
        try:
            for candidate in diva.search_host(host, query, limit):
                key = candidate.get("urn") or candidate.get("dissertation_url")
                if key and key not in seen:
                    seen.add(key)
                    results.append(candidate)
            if results and query.author:
                return results
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


def in_year_range(
    record: dict[str, Any],
    year_from: int | None,
    year_to: int | None,
    allow_missing_year: bool = False,
) -> bool:
    year = normalize_year(record.get("year"))
    if not year:
        return allow_missing_year
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


def known_person_matches_record(known_person: str, record: dict[str, Any]) -> bool:
    query_tokens = name_tokens_for_known_person(known_person)
    author_tokens = name_tokens_for_author(record.get("author"))
    author_token_set = set(author_tokens)
    if not query_tokens:
        return True

    if author_token_set:
        rare_query_surnames = rare_surname_tokens(query_tokens)
        if rare_query_surnames and tokens_match_all(rare_query_surnames, author_token_set):
            return True
        first = query_tokens[0]
        if token_matches_any(first, author_token_set) and tokens_have_overlap(query_tokens[1:], author_token_set):
            return True
        if (
            len(query_tokens) >= 2
            and token_matches_any(query_tokens[-1], {author_tokens[0]})
            and tokens_have_overlap(query_tokens[:-1], set(author_tokens[1:]))
        ):
            return True

    title_evidence = strong_dissertation_title(record)
    if title_evidence and tokens_have_overlap(query_tokens[1:] or query_tokens, author_token_set):
        return True
    if title_evidence and any(token in normalize_person_name_for_match(record.get("title")).split() for token in query_tokens[1:]):
        return True
    return False


def strong_dissertation_title(record: dict[str, Any]) -> bool:
    text = " ".join(
        clean_text(record.get(field)).lower()
        for field in ["title", "source", "publication_type", "document_type", "degree_type"]
    )
    return bool(clean_text(record.get("title"))) and (
        any(marker in text for marker in ["dissertation", "thesis", "avhandling"])
        or bool(record.get("dissertation_url"))
        or bool(record.get("urn"))
    )


def rare_surname_tokens(tokens: list[str]) -> set[str]:
    if len(tokens) <= 2:
        return set(tokens[1:])
    return set(tokens[1:])


def name_tokens(value: Any) -> list[str]:
    return normalize_person_name_for_match(value).split()


def name_tokens_for_author(value: Any) -> list[str]:
    text = clean_text(value)
    if "," in text:
        family, given = text.split(",", 1)
        return name_tokens(f"{given.strip()} {family.strip()}")
    return name_tokens(text)


def name_tokens_for_known_person(value: Any) -> list[str]:
    text = clean_text(value)
    if "," in text:
        family, given = text.split(",", 1)
        return name_tokens(f"{given.strip()} {family.strip()}")
    return name_tokens(person_name_from_known_person_input(text))


def token_matches(query_token: str, author_token: str) -> bool:
    if query_token == author_token:
        return True
    if len(query_token) == 1 and author_token.startswith(query_token):
        return True
    if len(author_token) == 1 and query_token.startswith(author_token):
        return True
    return False


def token_matches_any(query_token: str, author_tokens: set[str]) -> bool:
    return any(token_matches(query_token, author_token) for author_token in author_tokens)


def tokens_have_overlap(query_tokens: list[str] | set[str], author_tokens: set[str]) -> bool:
    return any(
        token_matches(query_token, author_token)
        for query_token in query_tokens
        for author_token in author_tokens
    )


def tokens_match_all(query_tokens: set[str], author_tokens: set[str]) -> bool:
    return all(token_matches_any(query_token, author_tokens) for query_token in query_tokens)


def log_filter_drop(record: dict[str, Any], reason: str) -> None:
    logger.info(
        "[discovery] filtered "
        f"reason={reason} pid={diva.pid_from_url(record.get('source_url') or record.get('dissertation_url'))} "
        f"title={clean_text(record.get('title'))!r}"
    )


def person_name_from_known_person_input(value: Any) -> str:
    tokens = normalize_person_name_for_search(value).split()
    if not tokens:
        return ""

    person_tokens = []
    institution_words = {
        "hogskolan",
        "hogskola",
        "universitet",
        "university",
        "college",
        "institute",
        "institutet",
        "karolinska",
        "boras",
        "borås",
        "i",
        "of",
    }
    for token in tokens:
        if re.fullmatch(r"(19|20)\d{2}", token):
            break
        if token in institution_words:
            break
        person_tokens.append(token)
    return " ".join(person_tokens or tokens)


def normalize_person_name_for_search(value: Any) -> str:
    text = clean_text(value).lower().replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", re.sub(r"[^\wåäöÅÄÖ ]+", " ", text, flags=re.UNICODE)).strip()


def normalize_person_name_for_match(value: Any) -> str:
    text = normalize_person_name_for_search(value)
    text = "".join(
        char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)
    )
    text = text.replace("å", "a").replace("ä", "a").replace("ö", "o")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", text)).strip()


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
        "abstract": clean_text(record.get("abstract")) or None,
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
        "relevance_status": "pending",
    }
    payload.update(duplicate)
    return payload


def normalized_discovery_results(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    identities: list[set[tuple[str, str]]] = []
    for candidate in candidates:
        normalized = discovery_result(candidate)
        candidate_identities = discovery_identities(normalized)
        duplicate_index = next(
            (
                index
                for index, existing_identities in enumerate(identities)
                if candidate_identities & existing_identities
            ),
            None,
        )
        if duplicate_index is None:
            unique.append(normalized)
            identities.append(candidate_identities)
            continue

        existing = unique[duplicate_index]
        existing["sources"] = list(
            dict.fromkeys([*(existing.get("sources") or []), *(normalized.get("sources") or [])])
        )
        for field, value in normalized.items():
            if field != "sources" and not existing.get(field) and value:
                existing[field] = value
        identities[duplicate_index].update(candidate_identities)
    return unique


def discovery_result(candidate: dict[str, Any]) -> dict[str, Any]:
    source_url = candidate.get("source_url") or candidate.get("dissertation_url")
    diva_id = diva.pid_from_url(source_url)
    author = clean_text(candidate.get("author")) or None
    year = normalize_year(candidate.get("year"))
    university = clean_text(candidate.get("university")) or None
    return {
        **candidate,
        "authors": [author] if author else [],
        "publication_year": year,
        "institution": university,
        "diva_id": diva_id,
        "source_url": source_url,
        "sources": [candidate.get("source")] if candidate.get("source") else [],
    }


def discovery_identities(candidate: dict[str, Any]) -> set[tuple[str, str]]:
    identities = set()
    if candidate.get("diva_id"):
        identities.add(("diva_id", clean_text(candidate["diva_id"]).lower()))
    if candidate.get("doi"):
        identities.add(("doi", clean_text(candidate["doi"]).lower()))
    title = comparable_text(candidate.get("title"))
    if title and candidate.get("publication_year"):
        identities.add(("title_year", f"{title}|{candidate['publication_year']}"))
    authors = candidate.get("authors") or []
    if title and authors:
        identities.add(("title_author", f"{title}|{normalize_person_name_for_match(authors[0])}"))
    return identities


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
    if existing and existing.relevance_status == "approved" and not existing.created_thesis_id:
        candidate.review_status = payload["review_status"]
        candidate.relevance_status = payload["relevance_status"]
    else:
        candidate.review_status = existing.review_status if existing else payload["review_status"]
        candidate.relevance_status = existing.relevance_status if existing else payload["relevance_status"]
    candidate.updated_at = now
    db.add(candidate)
    return candidate


def should_replace_source(existing: DiscoveryCandidate, payload: dict[str, Any]) -> bool:
    return source_rank(payload.get("source"), payload.get("source_host")) >= source_rank(
        existing.source,
        existing.source_host,
    )


def source_rank(source: str | None, source_host: str | None) -> int:
    if source == "avhandlingar.se":
        return 5
    if source == "DiVA":
        return 4
    if source_host and any(host in source_host for host in REPOSITORY_HOSTS):
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
    existing = db.query(DiscoveryCandidate).filter(or_(*clauses)).first() if clauses else None
    if existing or not payload.get("title"):
        return existing

    payload_diva_id = diva.pid_from_url(payload.get("source_url"))
    normalized_title = comparable_text(payload.get("title"))
    for candidate in db.query(DiscoveryCandidate).filter(DiscoveryCandidate.title.isnot(None)).all():
        if payload_diva_id and diva.pid_from_url(candidate.source_url) == payload_diva_id:
            return candidate
        if comparable_text(candidate.title) != normalized_title:
            continue
        same_year = bool(payload.get("year") and candidate.year == payload.get("year"))
        same_author = bool(
            payload.get("author")
            and candidate.author
            and author_similarity(payload.get("author"), candidate.author) >= 0.9
        )
        if same_year or same_author:
            return candidate
    return None


def list_discovery_candidates(db: Session, params: dict[str, Any]) -> list[DiscoveryCandidate]:
    query = db.query(DiscoveryCandidate)
    match_status = params.get("match_status")
    review_status = params.get("review_status")
    include_known = bool(params.get("include_known"))
    status_filter = params.get("status_filter") or "active"

    if match_status and match_status != "all":
        query = query.filter(DiscoveryCandidate.match_status == match_status)
    elif not include_known and status_filter != "all":
        query = query.filter(DiscoveryCandidate.match_status != "already_in_database")
    if review_status and review_status != "all":
        query = query.filter(DiscoveryCandidate.review_status == review_status)
    if status_filter == "active":
        active_status = DiscoveryCandidate.relevance_status.in_(["pending", "needs_review"])
        if include_known:
            query = query.filter(
                or_(
                    active_status,
                    DiscoveryCandidate.match_status == "already_in_database",
                )
            )
        else:
            query = query.filter(active_status)
        if not include_known:
            query = query.filter(DiscoveryCandidate.match_status != "already_in_database")
    elif status_filter == "approved":
        query = query.filter(DiscoveryCandidate.relevance_status == "approved")
    elif status_filter == "rejected":
        query = query.filter(DiscoveryCandidate.relevance_status == "rejected")
    elif status_filter != "all":
        query = query.filter(DiscoveryCandidate.relevance_status.in_(["pending", "needs_review"]))

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
        .filter(DiscoveryCandidate.relevance_status.in_(["pending", "needs_review"]))
        .count()
    )
    approved = (
        db.query(DiscoveryCandidate)
        .filter(DiscoveryCandidate.match_status != "already_in_database")
        .filter(DiscoveryCandidate.relevance_status == "approved")
        .filter(DiscoveryCandidate.created_thesis_id.isnot(None))
        .count()
    )
    rejected = (
        db.query(DiscoveryCandidate)
        .filter(DiscoveryCandidate.relevance_status == "rejected")
        .count()
    )
    possible_duplicates = (
        db.query(DiscoveryCandidate)
        .filter(DiscoveryCandidate.match_status == "possible_duplicate")
        .filter(DiscoveryCandidate.relevance_status.in_(["pending", "needs_review"]))
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
        "relevance_status": candidate.relevance_status,
        "created_thesis_id": candidate.created_thesis_id,
        "created_thesis_running_number": candidate.created_thesis_running_number,
        "created_at": candidate.created_at,
        "updated_at": candidate.updated_at,
    }


def ems_match_reason(candidate: DiscoveryCandidate) -> str:
    keywords = json.loads(candidate.matched_keywords or "[]")
    if keywords:
        return f"Matched EMS/prehospital keyword(s): {', '.join(keywords)}."
    return "Matched EMS/prehospital search criteria."


def approve_discovery_candidate(
    db: Session,
    candidate: DiscoveryCandidate,
    confirm_duplicate: bool = False,
) -> DiscoveryCandidate:
    if candidate.match_status == "already_in_database":
        raise ValueError("Known database matches cannot be approved as missing theses")
    if candidate.match_status == "possible_duplicate" and not confirm_duplicate:
        raise ValueError("Possible duplicates require explicit confirmation before approval")
    if candidate.relevance_status == "approved" and candidate.created_thesis_id:
        return candidate

    duplicate = classify_duplicate(candidate_record(candidate), db.query(Thesis).all())
    if duplicate["match_status"] == "already_in_database":
        candidate.match_status = "already_in_database"
        candidate.matched_existing_thesis_id = duplicate["matched_existing_thesis_id"]
        candidate.matched_existing_running_number = duplicate["matched_existing_running_number"]
        candidate.updated_at = datetime.now(timezone.utc)
        db.add(candidate)
        db.commit()
        raise ValueError("Candidate already matches an existing thesis")
    if duplicate["match_status"] == "possible_duplicate" and not confirm_duplicate:
        candidate.match_status = "possible_duplicate"
        candidate.similarity_to_existing = duplicate["similarity_to_existing"]
        candidate.matched_existing_thesis_id = duplicate["matched_existing_thesis_id"]
        candidate.matched_existing_running_number = duplicate["matched_existing_running_number"]
        candidate.updated_at = datetime.now(timezone.utc)
        db.add(candidate)
        db.commit()
        raise ValueError("Possible duplicates require explicit confirmation before approval")

    title = clean_text(candidate.title)
    author = clean_text(candidate.author)
    if not title or not author:
        raise ValueError("Title and author are required before approval")

    next_running_number = (db.query(func.max(Thesis.running_number)).scalar() or 0) + 1
    thesis = Thesis(
        running_number=next_running_number,
        title=title,
        author=author,
        university=clean_text(candidate.university) or None,
        year=candidate.year,
        degree_type=infer_degree_type(candidate.publication_type),
        category_id=None,
        subcategory_id=None,
        classification_status="needs_classification",
        source=candidate.source,
        abstract=candidate.abstract,
        dissertation_url=candidate.source_url,
        pdf_url=candidate.pdf_url,
        doi=candidate.doi,
        urn=candidate.urn,
    )
    db.add(thesis)
    db.flush()

    candidate.review_status = "approved"
    candidate.relevance_status = "approved"
    candidate.created_thesis_id = thesis.id
    candidate.created_thesis_running_number = thesis.running_number
    candidate.updated_at = datetime.now(timezone.utc)
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def reject_discovery_candidate(db: Session, candidate: DiscoveryCandidate) -> DiscoveryCandidate:
    candidate.review_status = "rejected"
    candidate.relevance_status = "rejected"
    candidate.updated_at = datetime.now(timezone.utc)
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def mark_discovery_candidate_needs_review(
    db: Session,
    candidate: DiscoveryCandidate,
) -> DiscoveryCandidate:
    candidate.review_status = "needs_review"
    candidate.relevance_status = "needs_review"
    candidate.updated_at = datetime.now(timezone.utc)
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def infer_degree_type(publication_type: Any) -> str:
    value = clean_text(publication_type).lower()
    if "licentiate" in value or "licentiat" in value:
        return "Licentiatavhandling"
    return "Doktorsavhandling"


def candidate_record(candidate: DiscoveryCandidate) -> dict[str, Any]:
    return {
        "title": candidate.title,
        "author": candidate.author,
        "university": candidate.university,
        "year": candidate.year,
        "doi": candidate.doi,
        "urn": candidate.urn,
        "dissertation_url": candidate.source_url,
        "pdf_url": candidate.pdf_url,
    }
