"""Tests for db.cache (memory path + DB-disabled / mocked DB)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

from db import cache
from tests.helpers import utc_dt


def _require(value: dict[str, Any] | None) -> dict[str, Any]:
    assert value is not None
    return value


class TestHashes:
    def test_image_url_hash_stable(self):
        a = cache.image_url_hash("https://example.com/a.jpg")
        b = cache.image_url_hash("https://example.com/a.jpg")
        assert a == b
        assert len(a) == 64

    def test_analysis_cache_key_differs_by_safe_search(self):
        url = "https://example.com/a.jpg"
        k1 = cache.analysis_cache_key(url, safe_search=True)
        k2 = cache.analysis_cache_key(url, safe_search=False)
        assert k1 != k2


class TestAnalysisCacheMemory:
    def setup_method(self):
        with cache._analysis_lock:
            cache._analysis_memory.clear()

    def test_set_and_get_roundtrip(self, monkeypatch: Any):
        monkeypatch.setattr(cache, "db_enabled", lambda: False)
        url = "https://example.com/img.jpg"
        snap = {"status": "done", "results": [{"url": "https://a.com"}]}
        cache.set_analysis_cache(url, snap, safe_search=True)
        got = _require(cache.get_analysis_cache(url, safe_search=True))
        assert got["status"] == "done"
        assert got["results"][0]["url"] == "https://a.com"

    def test_miss_when_empty(self, monkeypatch: Any):
        monkeypatch.setattr(cache, "db_enabled", lambda: False)
        assert cache.get_analysis_cache("https://none.example/x.jpg") is None

    def test_miss_when_expired(self, monkeypatch: Any):
        monkeypatch.setattr(cache, "db_enabled", lambda: False)
        monkeypatch.setattr(cache, "cache_ttl_seconds", lambda: 1)
        url = "https://example.com/old.jpg"
        cache.set_analysis_cache(url, {"status": "done"}, safe_search=True)
        key = cache.analysis_cache_key(url, safe_search=True)
        with cache._analysis_lock:
            ts, payload = cache._analysis_memory[key]
            cache._analysis_memory[key] = (ts - 10, payload)
        assert cache.get_analysis_cache(url, safe_search=True) is None


class TestEngineAndUrlCacheWithoutDb:
    def test_engine_get_set_noop_without_db(self, monkeypatch: Any):
        monkeypatch.setattr(cache, "db_enabled", lambda: False)
        assert cache.get_engine_cache("https://x.com/a.jpg", engine="google") is None
        cache.set_engine_cache("https://x.com/a.jpg", {"ok": True}, engine="google")
        assert cache.get_engine_cache("https://x.com/a.jpg", engine="google") is None

    def test_url_scrape_noop_without_db(self, monkeypatch: Any):
        monkeypatch.setattr(cache, "db_enabled", lambda: False)
        assert cache.get_url_scrape_cache("https://x.com/page") is None
        cache.set_url_scrape_cache(
            "https://x.com/page",
            platform="unknown",
            date_utc=utc_dt(2024, 1, 1),
            score=0.5,
            source="ld+json",
            extractor="static",
            confidence="confirmed",
        )
        assert cache.get_url_scrape_cache("https://x.com/page") is None


class TestCacheWithDbMocks:
    def test_get_engine_cache_hit(self, monkeypatch: Any):
        monkeypatch.setattr(cache, "db_enabled", lambda: True)
        monkeypatch.setattr(cache, "cache_ttl_seconds", lambda: 3600)
        cur = MagicMock()
        cur.fetchone.return_value = {"engine_payload": {"urls": ["https://a.com"]}}
        ctx = MagicMock()
        ctx.__enter__.return_value = cur
        ctx.__exit__.return_value = False
        monkeypatch.setattr(cache, "db_cursor", lambda: ctx)

        got = _require(
            cache.get_engine_cache(
                "https://img.com/x.jpg", engine="google_reverse_image"
            )
        )
        assert got == {"urls": ["https://a.com"]}
        cur.execute.assert_called_once()

    def test_get_engine_cache_json_string(self, monkeypatch: Any):
        monkeypatch.setattr(cache, "db_enabled", lambda: True)
        monkeypatch.setattr(cache, "cache_ttl_seconds", lambda: 3600)
        cur = MagicMock()
        cur.fetchone.return_value = {"engine_payload": '{"ok": true}'}
        ctx = MagicMock()
        ctx.__enter__.return_value = cur
        ctx.__exit__.return_value = False
        monkeypatch.setattr(cache, "db_cursor", lambda: ctx)

        assert cache.get_engine_cache("https://img.com/x.jpg", engine="yandex") == {
            "ok": True
        }

    def test_get_engine_cache_miss(self, monkeypatch: Any):
        monkeypatch.setattr(cache, "db_enabled", lambda: True)
        monkeypatch.setattr(cache, "cache_ttl_seconds", lambda: 3600)
        cur = MagicMock()
        cur.fetchone.return_value = None
        ctx = MagicMock()
        ctx.__enter__.return_value = cur
        ctx.__exit__.return_value = False
        monkeypatch.setattr(cache, "db_cursor", lambda: ctx)
        assert cache.get_engine_cache("https://img.com/x.jpg", engine="bing") is None

    def test_set_engine_cache_writes(self, monkeypatch: Any):
        monkeypatch.setattr(cache, "db_enabled", lambda: True)
        cur = MagicMock()
        ctx = MagicMock()
        ctx.__enter__.return_value = cur
        ctx.__exit__.return_value = False
        monkeypatch.setattr(cache, "db_cursor", lambda: ctx)

        with patch("psycopg.types.json.Jsonb", side_effect=lambda x: x):
            cache.set_engine_cache(
                "https://img.com/x.jpg", {"payload": 1}, engine="google_reverse_image"
            )
        cur.execute.assert_called_once()

    def test_get_url_scrape_cache_hit(self, monkeypatch: Any):
        monkeypatch.setattr(cache, "db_enabled", lambda: True)
        monkeypatch.setattr(cache, "cache_ttl_seconds", lambda: 3600)
        row = {
            "platform": "instagram",
            "date_utc": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "score": 0.8,
            "source": "time",
            "extractor": "dynamic",
            "confidence": "confirmed",
            "scraped_at": datetime.now(timezone.utc),
        }
        cur = MagicMock()
        cur.fetchone.return_value = row
        ctx = MagicMock()
        ctx.__enter__.return_value = cur
        ctx.__exit__.return_value = False
        monkeypatch.setattr(cache, "db_cursor", lambda: ctx)

        got = _require(cache.get_url_scrape_cache("https://instagram.com/p/abc"))
        assert got["platform"] == "instagram"
        assert got["score"] == 0.8

    def test_set_url_scrape_cache_writes(self, monkeypatch: Any):
        monkeypatch.setattr(cache, "db_enabled", lambda: True)
        cur = MagicMock()
        ctx = MagicMock()
        ctx.__enter__.return_value = cur
        ctx.__exit__.return_value = False
        monkeypatch.setattr(cache, "db_cursor", lambda: ctx)
        cache.set_url_scrape_cache(
            "https://example.com/post",
            platform="unknown",
            date_utc=utc_dt(2023, 5, 1),
            score=0.6,
            source="meta",
            extractor="static",
            confidence="provisional",
        )
        cur.execute.assert_called_once()

    def test_analysis_cache_db_get_and_set(self, monkeypatch: Any):
        monkeypatch.setattr(cache, "db_enabled", lambda: True)
        monkeypatch.setattr(cache, "cache_ttl_seconds", lambda: 3600)
        cur = MagicMock()
        cur.fetchone.return_value = {"snapshot": {"status": "done", "results": []}}
        ctx = MagicMock()
        ctx.__enter__.return_value = cur
        ctx.__exit__.return_value = False
        monkeypatch.setattr(cache, "db_cursor", lambda: ctx)

        got = _require(cache.get_analysis_cache("https://img.com/a.jpg", safe_search=True))
        assert got["status"] == "done"

        with patch("psycopg.types.json.Jsonb", side_effect=lambda x: x):
            cache.set_analysis_cache(
                "https://img.com/a.jpg", {"status": "done"}, safe_search=True
            )
        assert cur.execute.call_count >= 2
