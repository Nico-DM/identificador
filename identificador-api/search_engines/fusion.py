"""Merge reverse-image search results from multiple engines."""

from __future__ import annotations

from urllib.parse import urlparse

from logging_config import get_logger

from search_engines.base import SearchOutcome
from search_engines.utils import normalize_url

logger = get_logger(__name__)

DEFAULT_RRF_K = 60

LOW_QUALITY_HOSTS = ("google.com", "google.com.ar", "google.com.br")


def is_low_quality_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    if any(host == candidate or host.endswith(f".{candidate}") for candidate in LOW_QUALITY_HOSTS):
        return "/goto" in parsed.path.lower()
    return False


def merge_outcomes(
    labeled_outcomes: list[tuple[str, SearchOutcome]],
    *,
    rrf_k: int = DEFAULT_RRF_K,
) -> SearchOutcome:
    """Fuse URL lists with reciprocal rank fusion (RRF)."""
    scores: dict[str, float] = {}
    metadata: dict[str, dict] = {}
    url_by_norm: dict[str, str] = {}
    raw_by_engine: dict[str, dict] = {}

    for engine_name, outcome in labeled_outcomes:
        raw_by_engine[engine_name] = outcome.raw_payload
        for rank, url in enumerate(outcome.urls, start=1):
            if is_low_quality_url(url):
                continue
            norm = normalize_url(url)
            url_by_norm.setdefault(norm, url)
            scores[norm] = scores.get(norm, 0.0) + 1.0 / (rrf_k + rank)

            entry = metadata.setdefault(norm, {})
            for key, value in outcome.match_metadata.get(norm, {}).items():
                entry.setdefault(key, value)

    sorted_norms = sorted(scores, key=lambda norm: scores[norm], reverse=True)
    urls = [url_by_norm[norm] for norm in sorted_norms]

    return SearchOutcome(
        urls=urls,
        match_metadata={norm: metadata.get(norm, {}) for norm in sorted_norms},
        raw_payload={
            "fusion": {
                "engines": list(raw_by_engine.keys()),
                "rrf_k": rrf_k,
                "scores": {url_by_norm[norm]: round(scores[norm], 6) for norm in sorted_norms},
            },
            "engines": raw_by_engine,
        },
    )


def should_run_fallbacks(url_count: int, *, min_urls: int) -> bool:
    return url_count < min_urls
