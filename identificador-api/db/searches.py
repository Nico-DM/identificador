from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone

from db.connection import db_cursor
from db.json_util import from_jsonable, to_jsonable

_SEARCH_COLUMNS = (
    "search_id",
    "status",
    "phase",
    "image_url",
    "results",
    "raw_results",
    "error",
    "processed_urls",
    "total_urls",
    "static_total_urls",
    "match_metadata",
    "pending_dynamic",
    "deep_search_available",
    "created_at",
    "updated_at",
)


def _row_to_dict(row: dict) -> dict:
    data = {
        "status": row["status"],
        "phase": row["phase"],
        "image_url": row["image_url"],
        "results": from_jsonable(row["results"]),
        "raw_results": from_jsonable(row["raw_results"]),
        "error": row["error"],
        "processed_urls": row["processed_urls"],
        "total_urls": row["total_urls"],
        "static_total_urls": row["static_total_urls"],
        "match_metadata": from_jsonable(row["match_metadata"]) or {},
        "pending_dynamic": from_jsonable(row["pending_dynamic"]) or [],
        "deep_search_available": row["deep_search_available"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    if isinstance(data["created_at"], datetime) and data["created_at"].tzinfo is None:
        data["created_at"] = data["created_at"].replace(tzinfo=timezone.utc)
    if isinstance(data["updated_at"], datetime) and data["updated_at"].tzinfo is None:
        data["updated_at"] = data["updated_at"].replace(tzinfo=timezone.utc)
    return data


def _dict_to_row(search_id: str, data: dict) -> dict:
    from psycopg.types.json import Jsonb

    return {
        "search_id": search_id,
        "status": data["status"],
        "phase": data.get("phase", "static"),
        "image_url": data["image_url"],
        "results": Jsonb(to_jsonable(data.get("results"))),
        "raw_results": Jsonb(to_jsonable(data.get("raw_results"))),
        "error": data.get("error"),
        "processed_urls": data.get("processed_urls", 0),
        "total_urls": data.get("total_urls", 0),
        "static_total_urls": data.get("static_total_urls", 0),
        "match_metadata": Jsonb(to_jsonable(data.get("match_metadata") or {})),
        "pending_dynamic": Jsonb(to_jsonable(data.get("pending_dynamic") or [])),
        "deep_search_available": bool(data.get("deep_search_available", False)),
        "created_at": data["created_at"],
        "updated_at": data["updated_at"],
    }


def pg_get(search_id: str) -> dict | None:
    with db_cursor() as cur:
        cur.execute(
            f"SELECT {', '.join(_SEARCH_COLUMNS)} FROM searches WHERE search_id = %s",
            (search_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return _row_to_dict(row)


def pg_create(search_id: str, data: dict) -> None:
    row = _dict_to_row(search_id, data)
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO searches (
              search_id, status, phase, image_url, results, raw_results, error,
              processed_urls, total_urls, static_total_urls, match_metadata,
              pending_dynamic, deep_search_available, created_at, updated_at
            ) VALUES (
              %(search_id)s, %(status)s, %(phase)s, %(image_url)s, %(results)s,
              %(raw_results)s, %(error)s, %(processed_urls)s, %(total_urls)s,
              %(static_total_urls)s, %(match_metadata)s, %(pending_dynamic)s,
              %(deep_search_available)s, %(created_at)s, %(updated_at)s
            )
            """,
            row,
        )


def pg_save(search_id: str, data: dict) -> None:
    row = _dict_to_row(search_id, data)
    with db_cursor() as cur:
        cur.execute(
            """
            UPDATE searches SET
              status = %(status)s,
              phase = %(phase)s,
              image_url = %(image_url)s,
              results = %(results)s,
              raw_results = %(raw_results)s,
              error = %(error)s,
              processed_urls = %(processed_urls)s,
              total_urls = %(total_urls)s,
              static_total_urls = %(static_total_urls)s,
              match_metadata = %(match_metadata)s,
              pending_dynamic = %(pending_dynamic)s,
              deep_search_available = %(deep_search_available)s,
              updated_at = %(updated_at)s
            WHERE search_id = %(search_id)s
            """,
            row,
        )


def pg_prune(cutoff_ts: float) -> None:
    cutoff = datetime.fromtimestamp(cutoff_ts, tz=timezone.utc)
    with db_cursor() as cur:
        cur.execute("DELETE FROM searches WHERE created_at < %s", (cutoff,))


@contextmanager
def pg_session(search_id: str) -> Iterator[dict]:
    data = pg_get(search_id)
    if not data:
        yield None  # type: ignore[misc]
        return
    try:
        yield data
    finally:
        if data is not None:
            pg_save(search_id, data)
