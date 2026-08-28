import hashlib
import json
import threading
import time
from datetime import datetime, timezone

from db.config import cache_ttl_seconds, db_enabled
from db.connection import db_cursor
from db.json_util import from_jsonable, to_jsonable


def _normalize_url(url: str) -> str:
    from publication_scorer import normalize_url

    return normalize_url(url)


_CACHE_SELECT = """
SELECT platform, date_utc, score, source, extractor, confidence, scraped_at
FROM url_scrape_cache
WHERE url_normalized = %s
  AND scraped_at >= %s
"""


def image_url_hash(image_url: str) -> str:
    normalized = image_url.strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def analysis_cache_key(image_url: str, *, safe_search: bool = True) -> str:
    material = f"{image_url.strip()}\0safe={int(safe_search)}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


_analysis_memory: dict[str, tuple[float, dict]] = {}
_analysis_lock = threading.Lock()


def get_analysis_cache(image_url: str, *, safe_search: bool = True) -> dict | None:
    key = analysis_cache_key(image_url, safe_search=safe_search)
    cutoff = time.time() - cache_ttl_seconds()

    if db_enabled():
        cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc)
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT snapshot
                FROM image_analysis_cache
                WHERE cache_key = %s AND created_at >= %s
                """,
                (key, cutoff_dt),
            )
            row = cur.fetchone()
        if not row:
            return None
        snapshot = row["snapshot"]
        if isinstance(snapshot, str):
            snapshot = json.loads(snapshot)
        return from_jsonable(snapshot)

    with _analysis_lock:
        entry = _analysis_memory.get(key)
        if not entry or entry[0] < cutoff:
            return None
        return from_jsonable(entry[1])


def set_analysis_cache(
    image_url: str, snapshot: dict, *, safe_search: bool = True
) -> None:
    key = analysis_cache_key(image_url, safe_search=safe_search)
    encoded = to_jsonable(snapshot)
    now = time.time()

    if db_enabled():
        from psycopg.types.json import Jsonb

        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO image_analysis_cache (cache_key, image_url, safe_search, snapshot)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (cache_key) DO UPDATE SET
                  image_url = EXCLUDED.image_url,
                  safe_search = EXCLUDED.safe_search,
                  snapshot = EXCLUDED.snapshot,
                  created_at = now()
                """,
                (key, image_url.strip(), safe_search, Jsonb(encoded)),
            )
        return

    with _analysis_lock:
        _analysis_memory[key] = (now, encoded)


def get_engine_cache(image_url: str, *, engine: str) -> dict | None:
    if not db_enabled():
        return None
    cutoff = datetime.now(timezone.utc).timestamp() - cache_ttl_seconds()
    cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc)
    url_hash = image_url_hash(image_url)
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT engine_payload
            FROM image_engine_cache
            WHERE image_url_hash = %s
              AND engine = %s
              AND created_at >= %s
            """,
            (url_hash, engine, cutoff_dt),
        )
        row = cur.fetchone()
    if not row:
        return None
    payload = row["engine_payload"]
    if isinstance(payload, str):
        return json.loads(payload)
    return payload


def set_engine_cache(image_url: str, payload: dict, *, engine: str) -> None:
    if not db_enabled():
        return
    from psycopg.types.json import Jsonb

    url_hash = image_url_hash(image_url)
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO image_engine_cache (image_url_hash, image_url, engine, engine_payload)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (image_url_hash, engine) DO UPDATE SET
              image_url = EXCLUDED.image_url,
              engine_payload = EXCLUDED.engine_payload,
              created_at = now()
            """,
            (url_hash, image_url.strip(), engine, Jsonb(payload)),
        )


def get_url_scrape_cache(url: str) -> dict | None:
    if not db_enabled():
        return None
    normalized = _normalize_url(url)
    cutoff = datetime.now(timezone.utc).timestamp() - cache_ttl_seconds()
    cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc)
    with db_cursor() as cur:
        cur.execute(_CACHE_SELECT, (normalized, cutoff_dt))
        row = cur.fetchone()
    if not row:
        return None
    return dict(row)


def set_url_scrape_cache(
    url: str,
    *,
    platform: str,
    date_utc: datetime | None,
    score: float | None,
    source: str | None,
    extractor: str | None,
    confidence: str,
) -> None:
    if not db_enabled():
        return
    normalized = _normalize_url(url)
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO url_scrape_cache (
              url_normalized, platform, date_utc, score, source, extractor, confidence
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url_normalized) DO UPDATE SET
              platform = EXCLUDED.platform,
              date_utc = EXCLUDED.date_utc,
              score = EXCLUDED.score,
              source = EXCLUDED.source,
              extractor = EXCLUDED.extractor,
              confidence = EXCLUDED.confidence,
              scraped_at = now()
            """,
            (normalized, platform, date_utc, score, source, extractor, confidence),
        )
