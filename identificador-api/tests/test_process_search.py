"""Orchestration tests for search_service (engines/scrapers mocked)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import requests
from db import cache
from db.repository import search_create, search_get
from exceptions import IdentificadorError
from publication_scorer import _StaticPhaseOutcome
from search_engines.base import SearchOutcome
from search_service import (
    process_deep_search,
    process_search,
    prune_expired_searches,
    save_analysis_cache,
    set_search,
    start_search,
    update_search_progress,
)


def _require(value: dict[str, Any] | None) -> dict[str, Any]:
    assert value is not None
    return value


class FakeBackgroundTasks:
    def __init__(self):
        self.tasks: list[tuple] = []

    def add_task(self, fn, *args, **kwargs):
        self.tasks.append((fn, args, kwargs))


def _base_search(status: str = "processing", **extra) -> dict:
    now = datetime.now(timezone.utc)
    data = {
        "status": status,
        "phase": "static",
        "results": None,
        "raw_results": None,
        "error": None,
        "processed_urls": 0,
        "total_urls": 0,
        "static_total_urls": 0,
        "image_url": "https://cdn.example/img.jpg",
        "safe_search": True,
        "upload_object_path": None,
        "match_metadata": {},
        "pending_dynamic": [],
        "deep_search_available": False,
        "created_at": now,
        "updated_at": now,
    }
    data.update(extra)
    return data


class TestSetSearchAndProgress:
    def test_set_search_updates_status(self):
        search_id = "set-1"
        search_create(search_id, _base_search())
        set_search(search_id, "done", results=[{"url": "https://a.com"}], phase="complete")
        data = _require(search_get(search_id))
        assert data["status"] == "done"
        assert data["results"][0]["url"] == "https://a.com"
        assert data["phase"] == "complete"

    def test_update_progress_only_while_processing(self):
        search_id = "prog-1"
        search_create(search_id, _base_search(status="processing"))
        update_search_progress(search_id, results=[{"url": "https://x.com"}], processed=1, total=2)
        data = _require(search_get(search_id))
        assert data["processed_urls"] == 1
        assert data["total_urls"] == 2

        set_search(search_id, "done", phase="complete")
        update_search_progress(search_id, processed=99, total=99)
        assert _require(search_get(search_id))["processed_urls"] == 1


class TestSaveAnalysisCache:
    def setup_method(self):
        with cache._analysis_lock:
            cache._analysis_memory.clear()

    def test_saves_only_terminal_statuses(self, monkeypatch):
        monkeypatch.setattr(cache, "db_enabled", lambda: False)
        url = "https://cdn.example/cache.jpg"
        save_analysis_cache(url, True, {"status": "processing", "results": []})
        assert cache.get_analysis_cache(url) is None

        save_analysis_cache(
            url,
            True,
            {
                "status": "done",
                "phase": "complete",
                "results": [],
                "raw_results": [],
                "error": None,
                "processed_urls": 0,
                "total_urls": 0,
                "static_total_urls": 0,
                "match_metadata": {},
                "pending_dynamic": [],
                "deep_search_available": False,
            },
        )
        assert cache.get_analysis_cache(url) is not None


class TestStartSearch:
    def setup_method(self):
        with cache._analysis_lock:
            cache._analysis_memory.clear()

    def test_cache_hit(self, monkeypatch):
        monkeypatch.setattr(cache, "db_enabled", lambda: False)
        url = "https://cdn.example/hit.jpg"
        cache.set_analysis_cache(
            url,
            {
                "status": "done",
                "phase": "complete",
                "results": [{"url": "https://a.com"}],
                "raw_results": [],
                "error": None,
                "processed_urls": 1,
                "total_urls": 1,
                "static_total_urls": 1,
                "match_metadata": {},
                "pending_dynamic": [],
                "deep_search_available": False,
            },
            safe_search=True,
        )
        bg = FakeBackgroundTasks()
        delete = MagicMock()
        monkeypatch.setattr("search_service.delete_search_image", delete)

        result = start_search(bg, url, True, upload_object_path="uploads/tmp.jpg")
        assert result["cached"] is True
        assert result["status"] == "done"
        assert bg.tasks == []
        delete.assert_called_once_with("uploads/tmp.jpg")
        assert _require(search_get(result["search_id"]))["results"][0]["url"] == "https://a.com"

    def test_cache_miss_schedules_process(self, monkeypatch):
        monkeypatch.setattr(cache, "db_enabled", lambda: False)
        bg = FakeBackgroundTasks()
        result = start_search(bg, "https://cdn.example/miss.jpg", True)
        assert result["status"] == "processing"
        assert "cached" not in result
        assert len(bg.tasks) == 1
        fn, _, kwargs = bg.tasks[0]
        assert fn is process_search
        assert kwargs["safe_search"] is True


class TestProcessSearch:
    def test_completes_without_deep(self, monkeypatch):
        search_id = "proc-static"
        search_create(search_id, _base_search())

        class FakeEngine:
            name = "fake_engine"

            def search(self, image_url, *, safe_search=True):
                return SearchOutcome(
                    urls=["https://example.com/a", "https://example.com/b"],
                    match_metadata={
                        "https://example.com/a": {"site_name": "Example"},
                    },
                    raw_payload={},
                )

        monkeypatch.setattr("search_service.get_search_engine", lambda: FakeEngine())
        monkeypatch.setattr("search_service.SEARCH_MAX_CANDIDATE_URLS", 30)
        monkeypatch.setattr("search_service.SCRAPE_DYNAMIC_ENABLED", True)

        static_results = [
            {
                "link": "https://example.com/a",
                "platform": "unknown",
                "created_utc": None,
                "score": None,
                "source": "fake_engine",
                "confidence": "pending",
            }
        ]

        def fake_static(inputs, on_progress=None):
            if on_progress:
                on_progress(1, 2, static_results)
            return static_results, []

        monkeypatch.setattr("search_service.run_static_phase", fake_static)
        deep = MagicMock()
        monkeypatch.setattr("search_service.process_deep_search", deep)
        delete = MagicMock()
        monkeypatch.setattr("search_service.delete_search_image", delete)

        process_search(
            search_id,
            "https://cdn.example/img.jpg",
            upload_object_path="uploads/tmp.jpg",
        )

        data = _require(search_get(search_id))
        assert data["status"] == "done"
        assert data["phase"] == "complete"
        assert len(data["results"]) == 1
        deep.assert_not_called()
        delete.assert_called_once_with("uploads/tmp.jpg")

    def test_caps_urls_and_auto_deep(self, monkeypatch):
        search_id = "proc-deep"
        search_create(search_id, _base_search())

        class FakeEngine:
            name = "fake_engine"

            def search(self, image_url, *, safe_search=True):
                return SearchOutcome(
                    urls=[f"https://example.com/{i}" for i in range(5)],
                    match_metadata={},
                    raw_payload={},
                )

        monkeypatch.setattr("search_service.get_search_engine", lambda: FakeEngine())
        monkeypatch.setattr("search_service.SEARCH_MAX_CANDIDATE_URLS", 2)
        monkeypatch.setattr("search_service.SCRAPE_DYNAMIC_ENABLED", True)

        pending = [
            _StaticPhaseOutcome(
                result={"link": "https://instagram.com/p/1", "source": "fake"},
                url="https://instagram.com/p/1",
                platform="instagram",
                static_candidates=[],
                best_static=None,
                needs_dynamic=True,
                publication=None,
            )
        ]

        monkeypatch.setattr(
            "search_service.run_static_phase",
            lambda inputs, on_progress=None: ([], pending),
        )
        deep = MagicMock()
        monkeypatch.setattr("search_service.process_deep_search", deep)

        process_search(search_id, "https://cdn.example/img.jpg")
        deep.assert_called_once_with(search_id)
        data = _require(search_get(search_id))
        assert data["status"] == "deep_processing"
        assert data["static_total_urls"] == 2
        assert data["deep_search_available"] is True

    def test_identificador_error_sets_error_status(self, monkeypatch):
        search_id = "proc-err"
        search_create(search_id, _base_search())

        class BoomEngine:
            name = "boom"

            def search(self, image_url, *, safe_search=True):
                raise IdentificadorError("fallo de motor", code="ENGINE_ERROR")

        monkeypatch.setattr("search_service.get_search_engine", lambda: BoomEngine())
        process_search(search_id, "https://cdn.example/img.jpg")
        data = _require(search_get(search_id))
        assert data["status"] == "error"
        assert data["error"]

    def test_request_exception_sets_error_status(self, monkeypatch):
        search_id = "proc-net"
        search_create(search_id, _base_search())

        class BoomEngine:
            name = "boom"

            def search(self, image_url, *, safe_search=True):
                raise requests.RequestException("timeout")

        monkeypatch.setattr("search_service.get_search_engine", lambda: BoomEngine())
        process_search(search_id, "https://cdn.example/img.jpg")
        assert _require(search_get(search_id))["status"] == "error"


class TestProcessDeepSearch:
    def test_merges_and_completes(self, monkeypatch):
        search_id = "deep-1"
        pending = [
            {
                "result": {"link": "https://instagram.com/p/1", "source": "fake"},
                "url": "https://instagram.com/p/1",
                "platform": "instagram",
                "needs_dynamic": True,
                "best_static": None,
            }
        ]
        search_create(
            search_id,
            _base_search(
                status="deep_processing",
                phase="deep",
                raw_results=[
                    {
                        "link": "https://example.com/a",
                        "platform": "unknown",
                        "created_utc": None,
                        "score": None,
                        "source": "fake",
                        "confidence": "pending",
                    }
                ],
                pending_dynamic=pending,
                static_total_urls=1,
                deep_search_available=True,
            ),
        )

        updates = [
            {
                "link": "https://instagram.com/p/1",
                "platform": "instagram",
                "created_utc": None,
                "score": 0.4,
                "source": "fake",
                "confidence": "provisional",
            }
        ]
        monkeypatch.setattr(
            "search_service.run_dynamic_phase",
            lambda *args, **kwargs: updates,
        )
        monkeypatch.setattr(cache, "db_enabled", lambda: False)

        process_deep_search(search_id)
        data = _require(search_get(search_id))
        assert data["status"] == "done"
        assert data["deep_search_available"] is False
        assert data["pending_dynamic"] == []
        assert len(data["results"]) >= 1

    def test_missing_search_is_noop(self):
        process_deep_search("does-not-exist")

    def test_error_path(self, monkeypatch):
        search_id = "deep-err"
        search_create(
            search_id,
            _base_search(
                status="deep_processing",
                pending_dynamic=[
                    {
                        "result": {"link": "https://x.com/1", "source": "fake"},
                        "url": "https://x.com/1",
                        "platform": "x",
                        "needs_dynamic": True,
                        "best_static": None,
                    }
                ],
                deep_search_available=True,
            ),
        )

        def boom(*args, **kwargs):
            raise IdentificadorError("selenium down", code="DEEP_FAILED")

        monkeypatch.setattr("search_service.run_dynamic_phase", boom)
        process_deep_search(search_id)
        data = _require(search_get(search_id))
        assert data["status"] == "error"
        assert data["deep_search_available"] is False


class TestPruneExpired:
    def test_prune_removes_old(self):
        old = _base_search()
        old["created_at"] = datetime(2000, 1, 1, tzinfo=timezone.utc)
        search_create("old-search", old)
        search_create("new-search", _base_search())
        prune_expired_searches()
        assert search_get("old-search") is None
        assert search_get("new-search") is not None
