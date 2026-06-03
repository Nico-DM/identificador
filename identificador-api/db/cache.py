import hashlib
import json
from datetime import datetime, timezone

from db.config import cache_ttl_seconds, db_enabled
from db.connection import db_cursor


def _normalize_url(url: str) -> str:
    from identificador import normalize_url

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


def get_lens_cache(image_url: str) -> dict | None:
    if not db_enabled():
        return None
    cutoff = datetime.now(timezone.utc).timestamp() - cache_ttl_seconds()
    cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc)
    url_hash = image_url_hash(image_url)
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT serpapi_payload
            FROM image_lens_cache
            WHERE image_url_hash = %s AND created_at >= %s
            """,
            (url_hash, cutoff_dt),
        )
        row = cur.fetchone()
    if not row:
        return None
    payload = row["serpapi_payload"]
    if isinstance(payload, str):
        return json.loads(payload)
    return payload


def set_lens_cache(image_url: str, payload: dict) -> None:
    if not db_enabled():
        return
    from psycopg.types.json import Jsonb

    url_hash = image_url_hash(image_url)
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO image_lens_cache (image_url_hash, image_url, serpapi_payload)
            VALUES (%s, %s, %s)
            ON CONFLICT (image_url_hash) DO UPDATE SET
              image_url = EXCLUDED.image_url,
              serpapi_payload = EXCLUDED.serpapi_payload,
              created_at = now()
            """,
            (url_hash, image_url.strip(), Jsonb(payload)),
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
