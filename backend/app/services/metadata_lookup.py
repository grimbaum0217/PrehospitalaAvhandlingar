from app.models import Thesis
from app.providers import SearchQuery
from app.providers import avhandlingar, diva, swepub
from app.providers.common import MetadataError, normalize_candidate, score_candidate


PROVIDERS = (diva, swepub, avhandlingar)


def empty_candidate(source="Current local metadata"):
    return {
        "title": None,
        "author": None,
        "university": None,
        "year": None,
        "source": source,
        "dissertation_url": None,
        "pdf_url": None,
        "doi": None,
        "urn": None,
        "abstract": None,
        "confidence": 0,
    }


def lookup_metadata_candidates(thesis: Thesis):
    search_context = SearchQuery(
        title=thesis.title,
        author=thesis.author,
        university=thesis.university,
        year=thesis.year,
    )
    search_response = {
        "title": thesis.title,
        "author": thesis.author,
        "university": thesis.university,
        "year": thesis.year,
    }

    candidates = []
    errors = []

    if any(
        [
            thesis.dissertation_url,
            thesis.pdf_url,
            thesis.doi,
            thesis.urn,
            thesis.abstract,
        ]
    ):
        candidate = empty_candidate()
        candidate.update(
            {
                "title": thesis.title,
                "author": thesis.author,
                "university": thesis.university,
                "year": thesis.year,
                "source": "Current local metadata",
                "dissertation_url": thesis.dissertation_url,
                "pdf_url": thesis.pdf_url,
                "doi": thesis.doi,
                "urn": thesis.urn,
                "abstract": thesis.abstract,
                "confidence": 1,
            }
        )
        candidates.append(candidate)

    for provider in PROVIDERS:
        try:
            for candidate in provider.search(search_context):
                normalized = normalize_candidate(candidate, candidate.get("source") or provider.SOURCE)
                normalized["confidence"] = round(score_candidate(normalized, search_context), 3)
                candidates.append(normalized)
        except MetadataError as exc:
            errors.append({"source": provider.SOURCE, "error": str(exc)})

    candidates = deduplicate_candidates(candidates)
    candidates = apply_diva_preference(candidates)
    candidates.sort(
        key=lambda candidate: (
            candidate.get("confidence") or 0,
            source_priority(candidate.get("source")),
        ),
        reverse=True,
    )

    return {
        "search": search_response,
        "candidates": candidates,
        "errors": errors,
    }


def lookup_metadata_url(url: str):
    candidate = diva.lookup_url(url)
    return {
        "candidate": candidate,
        "candidates": [candidate],
    }


def deduplicate_candidates(candidates):
    by_key = {}
    for candidate in candidates:
        key = candidate_key(candidate)
        current = by_key.get(key)
        if current is None or candidate["confidence"] > current["confidence"]:
            by_key[key] = candidate
    return list(by_key.values())


def candidate_key(candidate):
    for field in ["doi", "urn", "pdf_url", "dissertation_url"]:
        if candidate.get(field):
            return field, candidate[field].lower()
    return (
        "title-author-year",
        (candidate.get("title") or "").lower(),
        (candidate.get("author") or "").lower(),
        candidate.get("year"),
    )


def source_priority(source):
    priorities = {
        "DiVA": 3,
        "SwePub": 2,
        "avhandlingar.se": 1,
        "Current local metadata": 4,
    }
    return priorities.get(source, 0)


def apply_diva_preference(candidates):
    has_diva_record = any(
        candidate.get("source") == "DiVA" and candidate.get("confidence", 0) >= 0.78
        for candidate in candidates
    )
    if not has_diva_record:
        return candidates

    adjusted = []
    for candidate in candidates:
        if candidate.get("source") != "DiVA":
            candidate = candidate.copy()
            candidate["confidence"] = round(min(candidate.get("confidence", 0), 0.74), 3)
        adjusted.append(candidate)
    return adjusted
