from __future__ import annotations

import json
import re
import ssl
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from difflib import SequenceMatcher
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi


USER_AGENT = "PrehospitalaAvhandlingar/0.1 dissertation metadata lookup"
TIMEOUT_SECONDS = 12
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

FIELD_NAMES = (
    "title",
    "author",
    "university",
    "year",
    "dissertation_url",
    "pdf_url",
    "urn",
    "doi",
    "abstract",
    "confidence",
    "source",
    "source_host",
)


@dataclass(frozen=True)
class SearchQuery:
    title: str | None = None
    author: str | None = None
    university: str | None = None
    year: int | str | None = None

    def terms(self) -> list[str]:
        return [
            clean_text(value)
            for value in [self.title, self.author, self.university, self.year]
            if clean_text(value)
        ]

    def as_text(self) -> str:
        return " ".join(self.terms())


class MetadataError(RuntimeError):
    pass


def blank_candidate(source: str) -> dict[str, Any]:
    candidate = {field: None for field in FIELD_NAMES}
    candidate["source"] = source
    candidate["confidence"] = 0
    return candidate


def normalize_candidate(candidate: dict[str, Any], source: str) -> dict[str, Any]:
    normalized = blank_candidate(source)
    normalized.update({key: candidate.get(key) for key in FIELD_NAMES if key in candidate})
    normalized["source"] = normalized.get("source") or source
    normalized["year"] = normalize_year(normalized.get("year"))
    normalized["confidence"] = round(float(normalized.get("confidence") or 0), 3)
    for key, value in list(normalized.items()):
        if isinstance(value, str):
            normalized[key] = clean_text(value) or None
    return normalized


def score_candidate(candidate: dict[str, Any], query: SearchQuery) -> float:
    score = 0.0
    title_score = similarity(query.title, candidate.get("title"))
    author_score = similarity(query.author, candidate.get("author"))
    university_score = similarity(query.university, candidate.get("university"))

    score += title_score * 0.55
    score += author_score * 0.22
    score += university_score * 0.08

    query_year = normalize_year(query.year)
    candidate_year = normalize_year(candidate.get("year"))
    if query_year and candidate_year:
        if query_year == candidate_year:
            score += 0.10
        elif abs(query_year - candidate_year) == 1:
            score += 0.04

    if candidate.get("pdf_url"):
        score += 0.03
    if candidate.get("dissertation_url"):
        score += 0.02
    if candidate.get("doi") or candidate.get("urn"):
        score += 0.02
    if candidate.get("abstract"):
        score += 0.02
    if candidate.get("source") == "DiVA" and title_score >= 0.9 and author_score >= 0.8:
        score += 0.08
    if candidate.get("source") == "DiVA" and query_year and candidate_year == query_year:
        score += 0.04

    return min(score, 1.0)


def similarity(left: Any, right: Any) -> float:
    left_text = comparable_text(left)
    right_text = comparable_text(right)
    if not left_text or not right_text:
        return 0.0
    if left_text in right_text or right_text in left_text:
        shorter = min(len(left_text), len(right_text))
        longer = max(len(left_text), len(right_text))
        return max(0.75, shorter / longer)
    sorted_left = " ".join(sorted(left_text.split()))
    sorted_right = " ".join(sorted(right_text.split()))
    return max(
        SequenceMatcher(None, left_text, right_text).ratio(),
        SequenceMatcher(None, sorted_left, sorted_right).ratio(),
    )


def comparable_text(value: Any) -> str:
    return re.sub(r"[^a-z0-9åäö]+", " ", clean_text(value).lower()).strip()


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = unescape(str(value))
    return re.sub(r"\s+", " ", text).strip()


def normalize_year(value: Any) -> int | None:
    if value is None:
        return None
    match = re.search(r"(19|20)\d{2}", str(value))
    return int(match.group(0)) if match else None


def absolute_url(base_url: str, url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("//"):
        return f"https:{url}"
    return f"{base_url.rstrip('/')}/{url.lstrip('/')}"


def fetch_text(url: str, params: dict[str, Any] | None = None) -> str:
    if params:
        url = f"{url}?{urlencode(params, doseq=True)}"
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS, context=SSL_CONTEXT) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise MetadataError(str(exc)) from exc


def fetch_json(url: str, params: dict[str, Any] | None = None) -> Any:
    return json.loads(fetch_text(url, params=params))


class MetaTagParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta: dict[str, str] = {}
        self.links: list[dict[str, str]] = []
        self.anchors: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        attr = {key.lower(): value or "" for key, value in attrs}
        if tag.lower() == "meta":
            name = attr.get("name") or attr.get("property")
            content = attr.get("content")
            if name and content and name not in self.meta:
                self.meta[name] = content
        elif tag.lower() == "link":
            self.links.append(attr)
        elif tag.lower() == "a":
            self.anchors.append(attr)


def extract_meta(html: str) -> MetaTagParser:
    parser = MetaTagParser()
    parser.feed(html)
    return parser


def first_value(data: dict[str, Any], names: list[str]) -> Any:
    for name in names:
        value = data.get(name)
        if value:
            return value
    lower_data = {key.lower(): value for key, value in data.items()}
    for name in names:
        value = lower_data.get(name.lower())
        if value:
            return value
    return None


def find_doi(text: str) -> str | None:
    match = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", text, flags=re.I)
    return match.group(0).rstrip(".,;") if match else None


def find_urn(text: str) -> str | None:
    match = re.search(r"\burn:[^\s<>'\"]+", text, flags=re.I)
    return match.group(0).rstrip(".,;") if match else None
