import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from db.config import db_enabled
from db import searches as pg

_searches_lock = threading.Lock()
_searches_db: dict[str, dict] = {}


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def search_get(search_id: str) -> dict | None:
    if db_enabled():
        return pg.pg_get(search_id)
    with _searches_lock:
        return _searches_db.get(search_id)


def search_create(search_id: str, data: dict) -> None:
    if db_enabled():
        pg.pg_create(search_id, data)
        return
    with _searches_lock:
        _searches_db[search_id] = data


@contextmanager
def search_session(search_id: str) -> Iterator[dict | None]:
    if db_enabled():
        with pg.pg_session(search_id) as data:
            yield data
        return

    with _searches_lock:
        data = _searches_db.get(search_id)
        yield data


def prune_searches(cutoff_ts: float) -> None:
    if db_enabled():
        pg.pg_prune(cutoff_ts)
        return
    with _searches_lock:
        stale = [
            key
            for key, value in _searches_db.items()
            if _ensure_utc(value["created_at"]).timestamp() < cutoff_ts
        ]
        for key in stale:
            _searches_db.pop(key, None)
