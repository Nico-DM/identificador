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
from env_util import env_str, parse_positive_int
from exceptions import IdentificadorError, classify_background_error
from logging_config import get_logger, search_id_context
from publication_scorer import (
    deserialize_pending_outcome,
    merge_publications,
    normalize_url,
    run_dynamic_phase,
    run_static_phase,
)
from scrape_config import SCRAPE_DYNAMIC_ENABLED
from search_engines import get_search_engine
from storage import delete_search_image

logger = get_logger(__name__)

SEARCH_TTL_SECONDS = int(env_str("SEARCH_TTL_SECONDS", "900"))
SEARCH_MAX_CANDIDATE_URLS = parse_positive_int(
    env_str("SEARCH_MAX_CANDIDATE_URLS"),
    30,
)
DEFAULT_BATCH_SIZE = 10


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def clamp_batch_size(value: int | None) -> int:
    if value is None or value < 1:
        return DEFAULT_BATCH_SIZE
    return min(int(value), SEARCH_MAX_CANDIDATE_URLS)


def parse_batch_size(value) -> int:
    if value is None:
        return DEFAULT_BATCH_SIZE
    if isinstance(value, bool):
        return DEFAULT_BATCH_SIZE
    if isinstance(value, int):
        return clamp_batch_size(value)
    try:
        return clamp_batch_size(int(str(value).strip(), 10))
    except (TypeError, ValueError):
        return DEFAULT_BATCH_SIZE


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
        "candidate_inputs": data.get("candidate_inputs") or [],
        "candidate_offset": data.get("candidate_offset", 0),
        "batch_size": data.get("batch_size", DEFAULT_BATCH_SIZE),
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
    candidates = data.get("candidate_inputs") or []
    offset = int(data.get("candidate_offset") or 0)
    batch_size = clamp_batch_size(data.get("batch_size"))
    total_candidates = len(candidates)
    remaining = max(0, total_candidates - offset)
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
        "batch": {
            "size": batch_size,
            "processed_candidates": min(offset, total_candidates),
            "total_candidates": total_candidates,
            "remaining": remaining,
        },
        "deep_search": {
            "available": deep_available,
            "pending_urls": pending_count if deep_available else 0,
        },
    }


def _finish_batch(
    search_id: str,
    *,
    final_raw: list,
    formatted: list,
    new_offset: int,
    total_candidates: int,
    batch_work_total: int,
) -> None:
    remaining = max(0, total_candidates - new_offset)
    with search_session(search_id) as current:
        if not current:
            return
        current["raw_results"] = final_raw
        current["results"] = formatted
        current["candidate_offset"] = new_offset
        current["static_total_urls"] = new_offset
        current["pending_dynamic"] = []
        current["deep_search_available"] = False
        current["processed_urls"] = batch_work_total
        current["total_urls"] = batch_work_total
        current["updated_at"] = now_utc()
        if remaining > 0:
            current["status"] = "batch_done"
            current["phase"] = "batch"
        else:
            current["status"] = "done"
            current["phase"] = "complete"
    search_persist(search_id, force=True)

    if remaining == 0:
        current = search_get(search_id)
        if current:
            save_analysis_cache(
                current["image_url"],
                current.get("safe_search", True),
                current,
            )


def process_next_batch(search_id: str) -> None:
    with search_id_context(search_id):
        try:
            current = search_get(search_id)
            if not current:
                return

            candidates = list(current.get("candidate_inputs") or [])
            offset = int(current.get("candidate_offset") or 0)
            batch_size = clamp_batch_size(current.get("batch_size"))
            match_metadata = dict(current.get("match_metadata") or {})
            existing_raw = list(current.get("raw_results") or [])
            batch = candidates[offset : offset + batch_size]

            if not batch:
                formatted = format_results(existing_raw, match_metadata)
                _finish_batch(
                    search_id,
                    final_raw=existing_raw,
                    formatted=formatted,
                    new_offset=offset,
                    total_candidates=len(candidates),
                    batch_work_total=0,
                )
                return

            batch_len = len(batch)
            with search_session(search_id) as cur:
                if not cur:
                    return
                cur["status"] = "processing"
                cur["phase"] = "static"
                cur["processed_urls"] = 0
                cur["total_urls"] = batch_len
                cur["error"] = None
                cur["updated_at"] = now_utc()
            search_persist(search_id, force=True)

            logger.info(
                "Starting candidate batch",
                extra={
                    "event": "batch_start",
                    "offset": offset,
                    "batch_size": batch_len,
                    "total_candidates": len(candidates),
                },
            )

            def on_static_progress(processed: int, total: int, partial: list) -> None:
                merged = merge_publications(existing_raw, partial)
                formatted_partial = format_results(merged, match_metadata)
                update_search_progress(
                    search_id,
                    results=formatted_partial,
                    processed=processed,
                    total=total,
                )

            static_results, pending_outcomes = run_static_phase(
                batch,
                on_progress=on_static_progress,
            )
            merged_after_static = merge_publications(existing_raw, static_results)

            deep_updates: list = []
            deep_total = 0
            if SCRAPE_DYNAMIC_ENABLED and pending_outcomes:
                deep_total = len(pending_outcomes)
                with search_session(search_id) as cur:
                    if not cur:
                        return
                    cur["status"] = "deep_processing"
                    cur["phase"] = "deep"
                    cur["processed_urls"] = batch_len
                    cur["total_urls"] = batch_len + deep_total
                    cur["updated_at"] = now_utc()
                search_persist(search_id, force=True)

                logger.info(
                    "Starting deep phase for batch",
                    extra={
                        "event": "batch_deep_start",
                        "pending_deep_count": deep_total,
                    },
                )

                def on_deep_progress(
                    processed: int, total: int, partial_updates: list
                ) -> None:
                    merged = merge_publications(merged_after_static, partial_updates)
                    formatted_partial = format_results(merged, match_metadata)
                    update_search_progress(
                        search_id,
                        results=formatted_partial,
                        processed=processed,
                        total=total,
                    )

                deep_updates = run_dynamic_phase(
                    pending_outcomes,
                    on_progress=on_deep_progress,
                    static_processed=batch_len,
                    static_total=batch_len,
                )

            final_raw = merge_publications(merged_after_static, deep_updates)
            formatted = format_results(final_raw, match_metadata)
            new_offset = offset + batch_len
            batch_work_total = batch_len + deep_total

            _finish_batch(
                search_id,
                final_raw=final_raw,
                formatted=formatted,
                new_offset=new_offset,
                total_candidates=len(candidates),
                batch_work_total=batch_work_total,
            )

            logger.info(
                "Candidate batch completed",
                extra={
                    "event": "batch_done",
                    "new_offset": new_offset,
                    "remaining": max(0, len(candidates) - new_offset),
                    "result_count": len(formatted),
                },
            )
        except (IdentificadorError, requests.RequestException) as exc:
            code, message = classify_background_error(exc)
            logger.error(
                message,
                extra={"event": "batch_failed", "code": code},
                exc_info=exc,
            )
            set_search(search_id, "error", error=message, phase="complete")
        except Exception as exc:
            code, message = classify_background_error(exc)
            logger.exception(
                "Unexpected error processing batch",
                extra={"event": "batch_failed", "code": code},
            )
            set_search(search_id, "error", error=message, phase="complete")


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
            if len(urls) > SEARCH_MAX_CANDIDATE_URLS:
                logger.info(
                    "Capping engine URLs",
                    extra={
                        "event": "engine_urls_capped",
                        "engine": engine.name,
                        "original_count": len(urls),
                        "kept": SEARCH_MAX_CANDIDATE_URLS,
                    },
                )
                urls = urls[:SEARCH_MAX_CANDIDATE_URLS]
            match_metadata = outcome.match_metadata
            logger.info(
                "Engine returned URLs",
                extra={
                    "event": "engine_results",
                    "engine": engine.name,
                    "url_count": len(urls),
                },
            )

            search_inputs = [
                {"link": url, "source": engine.name, "engine_rank": rank}
                for rank, url in enumerate(urls, start=1)
            ]

            with search_session(search_id) as current:
                if not current:
                    return
                current["candidate_inputs"] = search_inputs
                current["candidate_offset"] = 0
                current["match_metadata"] = match_metadata
                current["raw_results"] = []
                current["results"] = []
                current["pending_dynamic"] = []
                current["deep_search_available"] = False
                current["static_total_urls"] = 0
                current["updated_at"] = now_utc()
            search_persist(search_id, force=True)

            process_next_batch(search_id)
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
    """Legacy deep-search path (manual /deep). Prefer batch deep inside process_next_batch."""
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
    batch_size: int = DEFAULT_BATCH_SIZE,
    upload_object_path: str | None = None,
) -> dict:
    search_id = str(uuid.uuid4())
    now = now_utc()
    batch_size = clamp_batch_size(batch_size)

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
        extra={
            "event": "search_created",
            "image_url": image_url,
            "batch_size": batch_size,
        },
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
            "candidate_inputs": [],
            "candidate_offset": 0,
            "batch_size": batch_size,
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


def continue_search(background_tasks, search_id: str) -> dict:
    with search_session(search_id) as current:
        if not current:
            return {"search_id": search_id, "status": "error"}
        current["status"] = "processing"
        current["phase"] = "static"
        current["error"] = None
        current["processed_urls"] = 0
        current["total_urls"] = 0
        current["updated_at"] = now_utc()
    search_persist(search_id, force=True)

    background_tasks.add_task(process_next_batch, search_id)
    return {"search_id": search_id, "status": "processing"}


__all__ = [
    "DEFAULT_BATCH_SIZE",
    "build_results_response",
    "clamp_batch_size",
    "continue_search",
    "parse_batch_size",
    "process_deep_search",
    "process_next_batch",
    "process_search",
    "prune_expired_searches",
    "search_get",
    "start_search",
]
