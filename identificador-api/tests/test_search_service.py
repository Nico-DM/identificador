import pytest
from exceptions import ConfigurationError
from search_engines.factory import get_search_engine, registered_engines
from search_service import (
    analysis_snapshot,
    build_results_response,
    format_result_item,
    format_results,
    site_name_fallback,
)
from tests.helpers import utc_dt


class TestSiteNameFallback:
    def test_extracts_host(self):
        assert site_name_fallback("https://www.example.com/page", None) == "example.com"

    def test_platform_fallback(self):
        assert site_name_fallback("", "youtube") == "youtube"

    def test_unknown_fallback(self):
        assert site_name_fallback("", None) == "unknown"


class TestAnalysisSnapshot:
    def test_captures_key_fields(self):
        data = {
            "status": "done",
            "phase": "complete",
            "results": [{"url": "https://a.com"}],
            "raw_results": [],
            "error": None,
            "processed_urls": 5,
            "total_urls": 5,
            "static_total_urls": 5,
            "match_metadata": {"key": "val"},
            "pending_dynamic": [],
            "deep_search_available": False,
        }
        snap = analysis_snapshot(data)
        assert snap["status"] == "done"
        assert snap["processed_urls"] == 5
        assert snap["match_metadata"] == {"key": "val"}


class TestFormatResultItem:
    def test_formats_datetime(self):
        item = {
            "link": "https://example.com/post",
            "platform": "unknown",
            "created_utc": utc_dt(2024, 6, 15, 12, 0, 0),
            "score": 0.7,
            "source": "google_reverse_image",
            "confidence": "confirmed",
        }
        metadata = {
            "https://example.com/post": {
                "thumbnail": "https://cdn.com/t.jpg",
                "favicon": "https://cdn.com/f.ico",
                "site_name": "Example",
            }
        }
        result = format_result_item(item, metadata)
        assert result["date"] == "2024-06-15T12:00:00"
        assert result["thumbnail"] == "https://cdn.com/t.jpg"
        assert result["site_name"] == "Example"

    def test_site_name_fallback_when_no_metadata(self):
        item = {
            "link": "https://www.reddit.com/r/test",
            "platform": "reddit",
            "created_utc": None,
            "score": None,
            "source": "google",
        }
        result = format_result_item(item, {})
        assert result["site_name"] == "reddit.com"
        assert result["confidence"] == "pending"


class TestFormatResults:
    def test_maps_all_items(self):
        items = [
            {"link": "https://a.com", "platform": "unknown", "created_utc": None},
            {"link": "https://b.com", "platform": "unknown", "created_utc": None},
        ]
        results = format_results(items, {})
        assert len(results) == 2


class TestBuildResultsResponse:
    def test_includes_progress_and_deep_search(self):
        data = {
            "status": "static_done",
            "phase": "static",
            "results": [],
            "error": None,
            "processed_urls": 3,
            "total_urls": 5,
            "deep_search_available": True,
            "pending_dynamic": [{"url": "https://a.com"}, {"url": "https://b.com"}],
        }
        response = build_results_response("abc-123", data)
        assert response["search_id"] == "abc-123"
        assert response["status"] == "static_done"
        assert response["progress"]["processed"] == 3
        assert response["deep_search"]["available"] is True
        assert response["deep_search"]["pending_urls"] == 2

    def test_deep_search_hidden_when_unavailable(self):
        data = {
            "status": "done",
            "results": [],
            "error": None,
            "deep_search_available": False,
            "pending_dynamic": [{"url": "https://a.com"}],
        }
        response = build_results_response("id", data)
        assert response["deep_search"]["available"] is False
        assert response["deep_search"]["pending_urls"] == 0


class TestSearchEngineFactory:
    def test_registered_engines(self):
        engines = registered_engines()
        assert "google_reverse_image" in engines
        assert "bing_visual" in engines

    def test_get_default_engine(self):
        engine = get_search_engine("google_reverse_image")
        assert engine.name == "google_reverse_image"

    def test_bing_alias(self):
        engine = get_search_engine("bing_reverse_image")
        assert engine.name == "bing_reverse_image"
        assert get_search_engine("bing_visual").name == "bing_reverse_image"

    def test_unknown_engine_raises(self):
        with pytest.raises(ConfigurationError, match="desconocido"):
            get_search_engine("nonexistent_engine")
