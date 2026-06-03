from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from typing import Dict, List, Optional
from datetime import datetime, timezone
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
from db.cache import get_url_scrape_cache, set_url_scrape_cache

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


def _sort_publications(publications: List[dict]) -> None:
    publications.sort(
        key=lambda x: (
            x.get("created_utc") is None,
            x.get("created_utc") or datetime.max,
        )
    )


def _confidence_for_score(score: float | None) -> str:
    if score is None:
        return "pending"
    if score >= SCRAPE_STATIC_CONFIDENCE_THRESHOLD:
        return "confirmed"
    return "provisional"


def _candidate_from_cache(entry: dict, url: str) -> DateCandidate:
    date_value = entry["date_utc"]
    if isinstance(date_value, str):
        date_value = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
    return DateCandidate(
        date=_to_naive_utc(date_value),
        source=entry.get("source") or "cache",
        raw="",
        extractor=entry.get("extractor") or "static",
        url=url,
        score=float(entry.get("score") or 0.0),
    )


def _score_static_candidates(url: str, platform: str) -> tuple[List[DateCandidate], Optional[DateCandidate]]:
    cached = get_url_scrape_cache(url)
    if cached and cached.get("date_utc") is not None:
        best = _candidate_from_cache(cached, url)
        logger.info(f"Scrape estatico desde caché: {url}")
        return [best], best

    candidates = obtener_candidatas_estaticas(url)
    flags = classify_context(url, platform)
    for candidate in candidates:
        candidate.flags.update(flags)
        candidate.score = score_candidate(candidate, platform, flags)
    best_static = select_best_candidate(candidates)
    if best_static:
        set_url_scrape_cache(
            url,
            platform=platform,
            date_utc=best_static.date,
            score=best_static.score,
            source=best_static.source,
            extractor=best_static.extractor,
            confidence=_confidence_for_score(best_static.score),
        )
    return candidates, best_static


def _build_publication(
    result: dict,
    url: str,
    platform: str,
    best: DateCandidate,
    *,
    confidence: str | None = None,
) -> dict:
    publication = copy.copy(result)
    publication["created_utc"] = _to_naive_utc(best.date)
    publication["score"] = best.score
    publication["link"] = url
    publication["platform"] = platform
    publication["confidence"] = confidence or _confidence_for_score(best.score)
    return publication


def _build_pending_publication(
    result: dict,
    url: str,
    platform: str,
    *,
    confidence: str = "pending",
    best_static: Optional[DateCandidate] = None,
) -> dict:
    publication = copy.copy(result)
    publication["link"] = url
    publication["platform"] = platform
    publication["confidence"] = confidence
    if best_static:
        publication["created_utc"] = _to_naive_utc(best_static.date)
        publication["score"] = best_static.score
    else:
        publication["created_utc"] = None
        publication["score"] = None
    return publication


def _static_phase(result: dict) -> _StaticPhaseOutcome:
    url = result["link"]
    platform = detect_platform(url)
    logger.info(f"Fase estatica - Source: {result['source']}, Platform: {platform}, Link: {url}")

    static_candidates, best_static = _score_static_candidates(url, platform)
    needs_dynamic = not best_static or best_static.score < SCRAPE_STATIC_CONFIDENCE_THRESHOLD

    publication = None
    if best_static and not needs_dynamic:
        publication = _build_publication(result, url, platform, best_static, confidence="confirmed")
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

    return _build_publication(
        outcome.result,
        url,
        platform,
        best,
        confidence=_confidence_for_score(best.score),
    )


def _apply_static_outcome(
    outcome: _StaticPhaseOutcome,
    publicaciones: List[dict],
    pending_dynamic: List[_StaticPhaseOutcome],
) -> None:
    if outcome.publication:
        publicaciones.append(outcome.publication)
        _sort_publications(publicaciones)
        return

    if outcome.needs_dynamic and SCRAPE_DYNAMIC_ENABLED:
        pending_dynamic.append(outcome)
        if outcome.best_static:
            publicaciones.append(
                _build_pending_publication(
                    outcome.result,
                    outcome.url,
                    outcome.platform,
                    confidence="provisional",
                    best_static=outcome.best_static,
                )
            )
        else:
            publicaciones.append(
                _build_pending_publication(
                    outcome.result,
                    outcome.url,
                    outcome.platform,
                    confidence="pending",
                )
            )
        _sort_publications(publicaciones)
        return

    if outcome.best_static:
        publication = _build_publication(
            outcome.result,
            outcome.url,
            outcome.platform,
            outcome.best_static,
        )
        logger.info(
            f"Fecha estatica (dinamico desactivado): "
            f"{outcome.best_static.date} (score={outcome.best_static.score:.2f})"
        )
        publicaciones.append(publication)
        _sort_publications(publicaciones)
        return

    publicaciones.append(
        _build_pending_publication(
            outcome.result,
            outcome.url,
            outcome.platform,
            confidence="pending",
        )
    )
    _sort_publications(publicaciones)


def run_static_phase(results, on_progress=None) -> tuple[List[dict], List[_StaticPhaseOutcome]]:
    deduped = _dedupe_results(results)
    total = len(deduped)
    if total == 0:
        return [], []

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
                _apply_static_outcome(outcome, publicaciones, pending_dynamic)
                if on_progress:
                    on_progress(processed, total, list(publicaciones))

    return publicaciones, pending_dynamic


def run_dynamic_phase(
    pending_outcomes: List[_StaticPhaseOutcome],
    on_progress=None,
    *,
    static_processed: int = 0,
    static_total: int = 0,
) -> List[dict]:
    if not pending_outcomes:
        return []

    updates: List[dict] = []
    processed = 0
    total = len(pending_outcomes)
    lock = threading.Lock()

    dynamic_workers = min(SCRAPE_DYNAMIC_MAX_WORKERS, total)
    logger.info(
        f"Iniciando fase dinamica: {total} URLs, workers={dynamic_workers}"
    )

    with ThreadPoolExecutor(max_workers=dynamic_workers) as pool:
        futures = [pool.submit(_resolve_with_dynamic, item) for item in pending_outcomes]
        for future in as_completed(futures):
            publication = future.result()
            with lock:
                processed += 1
                if publication:
                    updates.append(publication)
                if on_progress:
                    on_progress(
                        static_processed + processed,
                        static_total + total,
                        list(updates),
                    )

    return updates


def merge_publications(existing: List[dict], updates: List[dict]) -> List[dict]:
    by_url: Dict[str, dict] = {}
    for item in existing:
        link = item.get("link")
        if link:
            by_url[normalize_url(link)] = copy.copy(item)

    for update in updates:
        link = update.get("link")
        if not link:
            continue
        key = normalize_url(link)
        current = by_url.get(key)
        if current is None:
            by_url[key] = copy.copy(update)
            continue

        current_score = current.get("score") or 0.0
        update_score = update.get("score") or 0.0
        current_confidence = current.get("confidence", "pending")
        update_has_date = update.get("created_utc") is not None

        if update_has_date and (
            current.get("created_utc") is None
            or update_score > current_score
            or current_confidence in {"pending", "provisional"}
        ):
            by_url[key] = copy.copy(update)

    merged = list(by_url.values())
    _sort_publications(merged)
    return merged


def serialize_pending_outcome(outcome: _StaticPhaseOutcome) -> dict:
    best = outcome.best_static
    best_data = None
    if best:
        best_data = {
            "date": best.date.isoformat(),
            "source": best.source,
            "raw": best.raw,
            "extractor": best.extractor,
            "url": best.url,
            "score": best.score,
            "flags": dict(best.flags),
        }
    return {
        "result": dict(outcome.result),
        "url": outcome.url,
        "platform": outcome.platform,
        "needs_dynamic": outcome.needs_dynamic,
        "best_static": best_data,
    }


def deserialize_pending_outcome(data: dict) -> _StaticPhaseOutcome:
    best_data = data.get("best_static")
    best_static = None
    if best_data:
        best_static = DateCandidate(
            date=datetime.fromisoformat(best_data["date"]),
            source=best_data["source"],
            raw=best_data["raw"],
            extractor=best_data["extractor"],
            url=best_data["url"],
            score=best_data.get("score", 0.0),
            flags=dict(best_data.get("flags") or {}),
        )
    return _StaticPhaseOutcome(
        result=data["result"],
        url=data["url"],
        platform=data["platform"],
        static_candidates=[],
        best_static=best_static,
        needs_dynamic=data.get("needs_dynamic", True),
        publication=None,
    )


def get_sorted_dates(results, on_progress=None):
    """Compatibilidad: fase estatica seguida de dinamica automatica si esta habilitada."""
    publicaciones, pending = run_static_phase(results, on_progress=on_progress)
    if pending and SCRAPE_DYNAMIC_ENABLED:
        updates = run_dynamic_phase(
            pending,
            on_progress=on_progress,
            static_processed=len(results),
            static_total=len(results),
        )
        return merge_publications(publicaciones, updates)
    return publicaciones
