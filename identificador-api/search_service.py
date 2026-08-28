import copy
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from db.cache import get_analysis_cache, set_analysis_cache
from db.repository import (
    prune_searches as repo_prune_searches,
)
from db.repository import (
    search_create,
    search_get,
    search_persist,
    search_session,
)
from env_util import env_str
from exceptions import IdentificadorError, classify_background_error
from logging_config import get_logger, search_id_context
from publication_scorer import (
    deserialize_pending_outcome,
    merge_publications,
    normalize_url,
    run_dynamic_phase,
    run_static_phase,
    serialize_pending_outcome,
)
from scrape_config import SCRAPE_DYNAMIC_ENABLED
from search_engines import get_search_engine
from storage import delete_search_image

logger = get_logger(__name__)

SEARCH_TTL_SECONDS = int(env_str("SEARCH_TTL_SECONDS", "900"))


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def prune_expired_searches() -> None:
    cutoff = now_utc().timestamp() - SEARCH_TTL_SECONDS
    repo_prune_searches(cutoff)


def site_name_fallback(url: str, platform: str | None) -> str:
    host = urlparse(url).netloc
    if host:
        return host.removeprefix("www.")
    return platform or "unknown"


def analysis_snapshot(data: dict) -> dict:
    return {
        "status": data["status"],
        "phase": data.get("phase", "complete"),
        "results": data.get("results"),
        "raw_results": data.get("raw_results"),
        "error": data.get("error"),
        "processed_urls": data.get("processed_urls", 0),
        "total_urls": data.get("total_urls", 0),
        "static_total_urls": data.get("static_total_urls", 0),
        "match_metadata": data.get("match_metadata") or {},
        "pending_dynamic": data.get("pending_dynamic") or [],
        "deep_search_available": bool(data.get("deep_search_available", False)),
    }


def save_analysis_cache(image_url: str, safe_search: bool, data: dict) -> None:
    if data.get("status") not in {"done", "static_done"}:
        return
    set_analysis_cache(image_url, analysis_snapshot(data), safe_search=safe_search)
    logger.info(
        "Analysis cached",
        extra={
            "event": "analysis_cached",
            "safe_search": "active" if safe_search else "off",
        },
    )


def set_search(
    search_id: str,
    status: str,
    *,
    results=None,
    error: str | None = None,
    phase: str | None = None,
) -> None:
    with search_session(search_id) as current:
        if not current:
            return
        current["status"] = status
        if results is not None:
            current["results"] = results
        current["error"] = error
        if phase is not None:
            current["phase"] = phase
        current["updated_at"] = now_utc()
    search_persist(search_id, force=True)


def update_search_progress(
    search_id: str,
    *,
    results: list | None = None,
    processed: int | None = None,
    total: int | None = None,
) -> None:
    with search_session(search_id) as current:
        if not current:
            return
        if current["status"] not in {"processing", "deep_processing"}:
            return
        if results is not None:
            current["results"] = results
        if processed is not None:
            current["processed_urls"] = processed
        if total is not None:
            current["total_urls"] = total
        current["updated_at"] = now_utc()
    search_persist(search_id)


def format_result_item(item: dict, match_metadata: dict) -> dict:
    created = item.get("created_utc")
    url = item.get("link")
    platform = item.get("platform")
    meta = match_metadata.get(normalize_url(url), {}) if url else {}
    return {
        "date": created.isoformat() if isinstance(created, datetime) else None,
        "platform": platform,
        "url": url,
        "score": item.get("score"),
        "source": item.get("source"),
        "confidence": item.get(
            "confidence", "pending" if created is None else "confirmed"
        ),
        "thumbnail": meta.get("thumbnail"),
        "favicon": meta.get("favicon"),
        "site_name": meta.get("site_name")
        or (site_name_fallback(url, platform) if url else (platform or "unknown")),
    }


def format_results(raw_results: list, match_metadata: dict) -> list:
    return [format_result_item(item, match_metadata) for item in raw_results]


def build_results_response(search_id: str, data: dict) -> dict:
    deep_available = data.get("deep_search_available", False)
    pending_count = len(data.get("pending_dynamic") or [])
    return {
        "search_id": search_id,
        "status": data["status"],
        "phase": data.get("phase", "complete"),
        "results": data["results"],
        "error": data["error"],
        "progress": {
            "processed": data.get("processed_urls", 0),
            "total": data.get("total_urls", 0),
        },
        "deep_search": {
            "available": deep_available,
            "pending_urls": pending_count if deep_available else 0,
        },
    }


def process_search(
    search_id: str,
    image_url: str,
    *,
    safe_search: bool = True,
    upload_object_path: str | None = None,
) -> None:
    with search_id_context(search_id):
        try:
            logger.info(
                "Starting search",
                extra={
                    "event": "search_start",
                    "image_url": image_url,
                    "safe_search": "active" if safe_search else "off",
                },
            )
            engine = get_search_engine()
            outcome = engine.search(image_url, safe_search=safe_search)
            urls = outcome.urls
            match_metadata = outcome.match_metadata
            logger.info(
                "Engine returned URLs",
                extra={
                    "event": "engine_results",
                    "engine": engine.name,
                    "url_count": len(urls),
                },
            )

            search_inputs = [{"link": url, "source": engine.name} for url in urls]
            total_urls = len(search_inputs)
            update_search_progress(search_id, results=[], processed=0, total=total_urls)

            def on_static_progress(processed: int, total: int, partial: list) -> None:
                formatted_partial = format_results(partial, match_metadata)
                update_search_progress(
                    search_id,
                    results=formatted_partial,
                    processed=processed,
                    total=total,
                )

            static_results, pending_outcomes = run_static_phase(
                search_inputs,
                on_progress=on_static_progress,
            )

            formatted = format_results(static_results, match_metadata)
            pending_serialized = [
                serialize_pending_outcome(item) for item in pending_outcomes
            ]
            deep_available = SCRAPE_DYNAMIC_ENABLED and len(pending_outcomes) > 0

            with search_session(search_id) as current:
                if not current:
                    return
                current["match_metadata"] = match_metadata
                current["pending_dynamic"] = pending_serialized
                current["deep_search_available"] = deep_available
                current["static_total_urls"] = total_urls
                current["raw_results"] = static_results
                current["results"] = formatted
                current["updated_at"] = now_utc()
            search_persist(search_id, force=True)

            logger.info(
                "Static phase completed",
                extra={
                    "event": "static_phase_done",
                    "result_count": len(static_results),
                    "pending_deep_count": len(pending_outcomes),
                },
            )

            if deep_available:
                set_search(search_id, "static_done", phase="static")
            else:
                set_search(search_id, "done", phase="complete")
            current = search_get(search_id)
            if current:
                save_analysis_cache(image_url, safe_search, current)
            logger.info(
                "Search static phase completed",
                extra={"event": "search_static_done"},
            )
        except (IdentificadorError, requests.RequestException) as exc:
            code, message = classify_background_error(exc)
            logger.error(
                message,
                extra={"event": "search_failed", "code": code},
                exc_info=exc,
            )
            set_search(
                search_id, "error", results=None, error=message, phase="complete"
            )
        except Exception as exc:
            code, message = classify_background_error(exc)
            logger.exception(
                "Unexpected error processing search",
                extra={"event": "search_failed", "code": code},
            )
            set_search(
                search_id,
                "error",
                results=None,
                error=message,
                phase="complete",
            )
        finally:
            if upload_object_path:
                delete_search_image(upload_object_path)


def process_deep_search(search_id: str) -> None:
    with search_id_context(search_id):
        try:
            current = search_get(search_id)
            if not current:
                return
            pending_data = list(current.get("pending_dynamic") or [])
            match_metadata = dict(current.get("match_metadata") or {})
            existing_raw = list(current.get("raw_results") or [])
            static_total = current.get("static_total_urls", 0)

            pending_outcomes = [
                deserialize_pending_outcome(item) for item in pending_data
            ]
            deep_total = len(pending_outcomes)
            update_search_progress(
                search_id,
                processed=static_total,
                total=static_total + deep_total,
            )

            def on_deep_progress(
                processed: int, total: int, partial_updates: list
            ) -> None:
                merged_raw = merge_publications(existing_raw, partial_updates)
                formatted = format_results(merged_raw, match_metadata)
                update_search_progress(
                    search_id,
                    results=formatted,
                    processed=processed,
                    total=total,
                )

            updates = run_dynamic_phase(
                pending_outcomes,
                on_progress=on_deep_progress,
                static_processed=static_total,
                static_total=static_total,
            )

            merged_raw = merge_publications(existing_raw, updates)
            formatted = format_results(merged_raw, match_metadata)

            with search_session(search_id) as current:
                if not current:
                    return
                current["raw_results"] = merged_raw
                current["results"] = formatted
                current["deep_search_available"] = False
                current["pending_dynamic"] = []
                current["processed_urls"] = static_total + deep_total
                current["total_urls"] = static_total + deep_total
                current["updated_at"] = now_utc()
            search_persist(search_id, force=True)

            set_search(
                search_id, "done", results=formatted, error=None, phase="complete"
            )
            current = search_get(search_id)
            if current:
                save_analysis_cache(
                    current["image_url"],
                    current.get("safe_search", True),
                    current,
                )
            logger.info(
                "Deep search completed",
                extra={"event": "deep_search_done", "result_count": len(formatted)},
            )
        except (IdentificadorError, requests.RequestException) as exc:
            code, message = classify_background_error(exc)
            logger.error(
                message,
                extra={"event": "deep_search_failed", "code": code},
                exc_info=exc,
            )
            with search_session(search_id) as current:
                if current:
                    current["deep_search_available"] = False
                    current["updated_at"] = now_utc()
            set_search(search_id, "error", error=message, phase="complete")
        except Exception as exc:
            code, message = classify_background_error(exc)
            logger.exception(
                "Unexpected error in deep search",
                extra={"event": "deep_search_failed", "code": code},
            )
            with search_session(search_id) as current:
                if current:
                    current["deep_search_available"] = False
                    current["updated_at"] = now_utc()
            set_search(search_id, "error", error=message, phase="complete")


def start_search(
    background_tasks,
    image_url: str,
    safe_search: bool,
    *,
    upload_object_path: str | None = None,
) -> dict:
    search_id = str(uuid.uuid4())
    now = now_utc()

    cached = get_analysis_cache(image_url, safe_search=safe_search)
    if cached is not None:
        if upload_object_path:
            delete_search_image(upload_object_path)
        data = copy.deepcopy(cached)
        data["image_url"] = image_url
        data["safe_search"] = safe_search
        data["created_at"] = now
        data["updated_at"] = now
        search_create(search_id, data)
        logger.info(
            "Search restored from cache",
            extra={
                "event": "search_cache_hit",
                "status": data["status"],
                "result_count": len(data.get("results") or []),
            },
        )
        return {"search_id": search_id, "status": data["status"], "cached": True}

    logger.info(
        "New search started",
        extra={"event": "search_created", "image_url": image_url},
    )
    search_create(
        search_id,
        {
            "status": "processing",
            "phase": "static",
            "results": None,
            "raw_results": None,
            "error": None,
            "processed_urls": 0,
            "total_urls": 0,
            "static_total_urls": 0,
            "image_url": image_url,
            "safe_search": safe_search,
            "upload_object_path": upload_object_path,
            "match_metadata": {},
            "pending_dynamic": [],
            "deep_search_available": False,
            "created_at": now,
            "updated_at": now,
        },
    )

    background_tasks.add_task(
        process_search,
        search_id,
        image_url,
        safe_search=safe_search,
        upload_object_path=upload_object_path,
    )

    return {"search_id": search_id, "status": "processing"}


__all__ = [
    "build_results_response",
    "process_deep_search",
    "prune_expired_searches",
    "search_get",
    "start_search",
]
