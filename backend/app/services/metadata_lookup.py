from app.models import Thesis


def empty_candidate():
    return {
        "title": None,
        "source": None,
        "dissertation_url": None,
        "pdf_url": None,
        "doi": None,
        "urn": None,
        "abstract": None,
        "confidence": 0,
    }


def lookup_metadata_candidates(thesis: Thesis):
    search_context = {
        "title": thesis.title,
        "author": thesis.author,
        "university": thesis.university,
        "year": thesis.year,
    }

    candidates = []

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

    return {
        "search": search_context,
        "candidates": candidates,
    }
