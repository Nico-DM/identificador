import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from db.config import db_enabled
from db import searches as pg

_searches_lock = threading.Lock()
_searches_db: dict[str, dict] = {}
_last_persist: dict[str, float] = {}
_PROGRESS_PERSIST_INTERVAL = 2.0


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _load_from_pg(search_id: str) -> dict | None:
    data = pg.pg_get(search_id)
    if data is not None:
        with _searches_lock:
            _searches_db[search_id] = data
    return data


def search_persist(search_id: str, *, force: bool = False) -> None:
    if not db_enabled():
        return
    with _searches_lock:
        data = _searches_db.get(search_id)
        if not data:
            return
        now = time.monotonic()
        if not force and now - _last_persist.get(search_id, 0) < _PROGRESS_PERSIST_INTERVAL:
            return
        _last_persist[search_id] = now
    pg.pg_save(search_id, data)


def search_get(search_id: str) -> dict | None:
    with _searches_lock:
        cached = _searches_db.get(search_id)
    if cached is not None:
        return cached
    if db_enabled():
        return _load_from_pg(search_id)
    return None


def search_create(search_id: str, data: dict) -> None:
    with _searches_lock:
        _searches_db[search_id] = data
        if db_enabled():
            _last_persist[search_id] = time.monotonic()
    if db_enabled():
        pg.pg_create(search_id, data)


@contextmanager
def search_session(search_id: str) -> Iterator[dict | None]:
    with _searches_lock:
        data = _searches_db.get(search_id)
    if data is None and db_enabled():
        data = _load_from_pg(search_id)
    yield data


def prune_searches(cutoff_ts: float) -> None:
    if db_enabled():
        pg.pg_prune(cutoff_ts)
    with _searches_lock:
        stale = [
            key
            for key, value in _searches_db.items()
            if _ensure_utc(value["created_at"]).timestamp() < cutoff_ts
        ]
        for key in stale:
            _searches_db.pop(key, None)
            _last_persist.pop(key, None)
