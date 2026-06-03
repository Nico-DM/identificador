from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from typing import Dict, List, Optional
from datetime import timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import copy
import logging
import threading

from scraper_estatico import obtener_candidatas_estaticas
from scraper_dinamico import obtener_candidatas_dinamicas
from modelos import DateCandidate
from scrape_config import (
    SCRAPE_DYNAMIC_ENABLED,
    SCRAPE_DYNAMIC_MAX_WORKERS,
    SCRAPE_STATIC_CONFIDENCE_THRESHOLD,
    SCRAPE_STATIC_MAX_WORKERS,
)

logger = logging.getLogger(__name__)


def _to_naive_utc(dt):
    """Convierte cualquier datetime a naive UTC."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "igshid",
    "ref",
    "src",
    "spm",
    "mkt_tok",
    "mc_cid",
    "mc_eid",
}

SOURCE_SCORE = {
    "ld+json": 0.5,
    "meta": 0.4,
    "time": 0.3,
    "script-json": 0.25,
    "script-regex": 0.15,
    "visible-text": 0.1,
    "time-datetime": 0.3,
    "time-text": 0.2,
    "texto": 0.1,
}

EXTRACTOR_SCORE = {
    "static": 0.1,
    "dynamic": 0.2,
}

# Plataformas cuyo HTML inicial suele incluir fechas fiables en meta/time/ld+json.
PLATFORM_STATIC_BONUS = {"youtube", "reddit", "deviantart"}

# Fuentes estructuradas presentes en HTML sin JS; merecen confianza en fase estatica.
STATIC_STRUCTURED_SOURCES = {"meta", "ld+json", "time"}


@dataclass
class _StaticPhaseOutcome:
    result: dict
    url: str
    platform: str
    static_candidates: List[DateCandidate]
    best_static: Optional[DateCandidate]
    needs_dynamic: bool
    publication: Optional[dict]


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k not in TRACKING_PARAMS]
    clean = parsed._replace(query=urlencode(query), fragment="")
    return urlunparse(clean)


def detect_platform(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "instagram.com" in host:
        return "instagram"
    if "reddit.com" in host:
        return "reddit"
    if "deviantart.com" in host:
        return "deviantart"
    if "x.com" in host or "twitter.com" in host:
        return "x"
    if "tiktok.com" in host:
        return "tiktok"
    if "facebook.com" in host:
        return "facebook"
    return "unknown"


def classify_context(url: str, platform: str) -> Dict[str, bool]:
    path = urlparse(url).path.lower()
    flags = {
        "is_comment": False,
        "is_reply": False,
        "is_embed": False,
        "is_share": False,
        "is_profile": False,
    }

    if "embed" in path:
        flags["is_embed"] = True
    if any(token in path for token in ("/replies", "/reply")):
        flags["is_reply"] = True
    if "comment" in path and platform != "reddit":
        flags["is_comment"] = True
    if any(token in path for token in ("/share", "/repost", "/retweet", "/shares")):
        flags["is_share"] = True

    segments = [s for s in path.split("/") if s]
    if len(segments) == 1 and platform in {"instagram", "x", "tiktok"}:
        flags["is_profile"] = True

    return flags


def _normalize_source(source: str) -> str:
    if source.startswith("meta:"):
        return "meta"
    if source in {"time-datetime", "time-text"}:
        return "time"
    return source


def score_candidate(candidate: DateCandidate, platform: str, flags: Dict[str, bool]) -> float:
    normalized = _normalize_source(candidate.source)
    score = 0.0
    score += SOURCE_SCORE.get(normalized, SOURCE_SCORE.get(candidate.source, 0.05))
    score += EXTRACTOR_SCORE.get(candidate.extractor, 0.0)

    if platform in PLATFORM_STATIC_BONUS and normalized in STATIC_STRUCTURED_SOURCES:
        score += 0.2

    if candidate.extractor == "static" and normalized in {"meta", "ld+json"}:
        score += 0.1

    if flags.get("is_comment"):
        score -= 0.5
    if flags.get("is_reply"):
        score -= 0.4
    if flags.get("is_share"):
        score -= 0.3
    if flags.get("is_embed"):
        score -= 0.2
    if flags.get("is_profile"):
        score -= 0.2

    return max(score, 0.0)


def select_best_candidate(candidates: List[DateCandidate], threshold: float = 0.45):
    if not candidates:
        return None

    filtered = [c for c in candidates if c.score >= threshold]
    if not filtered:
        filtered = candidates

    filtered.sort(key=lambda c: (c.date, -c.score))
    return filtered[0]


def _dedupe_results(results) -> list:
    deduped = []
    seen_urls = set()
    for result in results:
        url = normalize_url(result["link"])
        if url in seen_urls:
            logger.debug(f"URL duplicada, ignorando: {url}")
            continue
        seen_urls.add(url)
        item = copy.copy(result)
        item["link"] = url
        deduped.append(item)
    return deduped


def _score_static_candidates(url: str, platform: str) -> tuple[List[DateCandidate], Optional[DateCandidate]]:
    candidates = obtener_candidatas_estaticas(url)
    flags = classify_context(url, platform)
    for candidate in candidates:
        candidate.flags.update(flags)
        candidate.score = score_candidate(candidate, platform, flags)
    best_static = select_best_candidate(candidates)
    return candidates, best_static


def _build_publication(result: dict, url: str, platform: str, best: DateCandidate) -> dict:
    publication = copy.copy(result)
    publication["created_utc"] = _to_naive_utc(best.date)
    publication["score"] = best.score
    publication["link"] = url
    publication["platform"] = platform
    return publication


def _static_phase(result: dict) -> _StaticPhaseOutcome:
    url = result["link"]
    platform = detect_platform(url)
    logger.info(f"Fase estatica - Source: {result['source']}, Platform: {platform}, Link: {url}")

    static_candidates, best_static = _score_static_candidates(url, platform)
    needs_dynamic = not best_static or best_static.score < SCRAPE_STATIC_CONFIDENCE_THRESHOLD

    publication = None
    if best_static and not needs_dynamic:
        publication = _build_publication(result, url, platform, best_static)
        logger.info(f"Fecha estatica: {best_static.date} (score={best_static.score:.2f})")
    elif needs_dynamic:
        static_score = best_static.score if best_static else 0.0
        logger.info(
            f"Fecha estatica provisional (score={static_score:.2f}); pendiente dinamico: {url}"
        )
    else:
        logger.debug(f"No se encontro fecha estatica para: {url}")

    return _StaticPhaseOutcome(
        result=result,
        url=url,
        platform=platform,
        static_candidates=static_candidates,
        best_static=best_static,
        needs_dynamic=needs_dynamic,
        publication=publication,
    )


def _resolve_with_dynamic(outcome: _StaticPhaseOutcome) -> Optional[dict]:
    url = outcome.url
    platform = outcome.platform
    best_static = outcome.best_static
    logger.info(f"Fase dinamica - Platform: {platform}, Link: {url}")

    dynamic = obtener_candidatas_dinamicas(url)
    flags = classify_context(url, platform)
    dynamic_scored: List[DateCandidate] = []
    for candidate in dynamic:
        candidate.flags.update(flags)
        candidate.score = score_candidate(candidate, platform, flags)
        dynamic_scored.append(candidate)

    best_dynamic = select_best_candidate(dynamic_scored) if dynamic_scored else None

    if best_dynamic and best_static:
        if best_dynamic.score > best_static.score:
            best = best_dynamic
            logger.info(
                f"Fecha dinamica (mejora estatica): {best.date} (score={best.score:.2f})"
            )
        else:
            best = best_static
            logger.info(
                f"Fecha estatica conservada: {best.date} (score={best.score:.2f})"
            )
    elif best_dynamic:
        best = best_dynamic
        logger.info(f"Fecha dinamica: {best.date} (score={best.score:.2f})")
    elif best_static:
        best = best_static
        logger.info(
            f"Fecha estatica (fallback): {best.date} (score={best.score:.2f})"
        )
    else:
        logger.debug(f"No se encontro fecha para: {url}")
        return None

    return _build_publication(outcome.result, url, platform, best)


def get_sorted_dates(results, on_progress=None):
    deduped = _dedupe_results(results)
    total = len(deduped)
    if total == 0:
        return []

    publicaciones: List[dict] = []
    processed = 0
    lock = threading.Lock()
    pending_dynamic: List[_StaticPhaseOutcome] = []

    static_workers = min(SCRAPE_STATIC_MAX_WORKERS, total)
    logger.info(
        f"Iniciando fase estatica: {total} URLs, workers={static_workers}, "
        f"umbral={SCRAPE_STATIC_CONFIDENCE_THRESHOLD}"
    )

    with ThreadPoolExecutor(max_workers=static_workers) as pool:
        futures = [pool.submit(_static_phase, item) for item in deduped]
        for future in as_completed(futures):
            outcome = future.result()
            with lock:
                processed += 1
                if outcome.publication:
                    publicaciones.append(outcome.publication)
                    publicaciones.sort(key=lambda x: x["created_utc"])
                elif outcome.needs_dynamic and SCRAPE_DYNAMIC_ENABLED:
                    pending_dynamic.append(outcome)
                elif outcome.best_static:
                    publication = _build_publication(
                        outcome.result, outcome.url, outcome.platform, outcome.best_static
                    )
                    logger.info(
                        f"Fecha estatica (dinamico desactivado): "
                        f"{outcome.best_static.date} (score={outcome.best_static.score:.2f})"
                    )
                    publicaciones.append(publication)
                    publicaciones.sort(key=lambda x: x["created_utc"])
                if on_progress:
                    on_progress(processed, total, list(publicaciones))

    if pending_dynamic and SCRAPE_DYNAMIC_ENABLED:
        dynamic_workers = min(SCRAPE_DYNAMIC_MAX_WORKERS, len(pending_dynamic))
        logger.info(
            f"Iniciando fase dinamica: {len(pending_dynamic)} URLs, workers={dynamic_workers}"
        )
        with ThreadPoolExecutor(max_workers=dynamic_workers) as pool:
            futures = [pool.submit(_resolve_with_dynamic, item) for item in pending_dynamic]
            for future in as_completed(futures):
                publication = future.result()
                with lock:
                    if publication:
                        publicaciones.append(publication)
                        publicaciones.sort(key=lambda x: x["created_utc"])
                    if on_progress:
                        on_progress(processed, total, list(publicaciones))

    return publicaciones
