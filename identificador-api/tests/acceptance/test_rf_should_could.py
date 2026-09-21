"""Should / Could RF acceptance criteria (RF-007 … RF-011)."""

from __future__ import annotations

import pytest
import storage
from logging_config import configure_logging, get_logger
from models import DateCandidate
from publication_scorer import _build_publication, _confidence_for_score
from tests.acceptance.conftest import _poll_done
from tests.helpers import utc_dt

pytestmark = pytest.mark.acceptance

JPEG = b"\xff\xd8\xff" + b"\x00" * 32
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
WEBP = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 8


@pytest.mark.rf("RF-007", title="Múltiples resultados ordenados")
@pytest.mark.usefixtures("require_serpapi")
class TestRF007MultipleResults:
    def test_api_returns_list_of_candidates(self, api_client, acceptance_image_url):
        create = api_client.post(
            "/api/search",
            json={"image_url": acceptance_image_url, "safe_search": True},
        )
        assert create.status_code == 200
        payload = _poll_done(api_client, create.json()["search_id"])
        assert payload["status"] == "done", payload.get("error")
        results = payload.get("results") or []
        assert len(results) >= 2, "Se esperaban múltiples candidatos (RF-007)"


@pytest.mark.rf("RF-008", title="Indicadores de confiabilidad")
class TestRF008Confidence:
    def test_confidence_levels_from_score(self):
        assert _confidence_for_score(0.9) in {"confirmed", "provisional", "pending"}
        assert isinstance(_confidence_for_score(0.2), str)

    def test_publication_exposes_confidence(self):
        result = {"link": "https://example.com/p", "source": "test", "engine_rank": 1}
        best = DateCandidate(
            date=utc_dt(2018, 5, 1),
            source="ld+json",
            raw="2018-05-01",
            extractor="static",
            url="https://example.com/p",
            score=0.8,
        )
        pub = _build_publication(result, result["link"], "unknown", best)
        assert pub["confidence"] in {"confirmed", "provisional", "pending"}
        assert pub.get("score") is not None


@pytest.mark.rf("RF-009", title="Múltiples formatos de imagen")
class TestRF009Formats:
    def test_upload_validation_jpg_png_webp(self):
        assert storage.validate_upload(JPEG, "a.jpg")[0] in {".jpg", ".jpeg"}
        assert storage.validate_upload(PNG, "a.png")[0] == ".png"
        assert storage.validate_upload(WEBP, "a.webp")[0] == ".webp"

    def test_url_extensions_accepted(self):
        from image_validation import IMAGE_EXTENSIONS

        for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            assert ext in IMAGE_EXTENSIONS


@pytest.mark.rf("RF-010", title="Caché de resultados para consultas repetidas")
class TestRF010Cache:
    def test_memory_analysis_cache_roundtrip(self, monkeypatch):
        from db import cache

        monkeypatch.setattr(cache, "db_enabled", lambda: False)
        with cache._analysis_lock:
            cache._analysis_memory.clear()

        url = "https://example.com/acceptance-cache.jpg"
        snap = {
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
        }
        cache.set_analysis_cache(url, snap, safe_search=True)
        got = cache.get_analysis_cache(url, safe_search=True)
        assert got is not None
        assert got["status"] == "done"

    @pytest.mark.usefixtures("require_serpapi")
    def test_second_search_can_hit_cache(self, api_client, acceptance_image_url, monkeypatch):
        from db import cache
        from search_service import start_search

        monkeypatch.setattr(cache, "db_enabled", lambda: False)
        with cache._analysis_lock:
            cache._analysis_memory.clear()

        first = api_client.post(
            "/api/search",
            json={"image_url": acceptance_image_url, "safe_search": True},
        )
        assert first.status_code == 200
        _poll_done(api_client, first.json()["search_id"])

        class BG:
            def add_task(self, *args, **kwargs):
                raise AssertionError("No debe encolar process_search en cache hit")

        second = start_search(BG(), acceptance_image_url, True)
        assert second.get("cached") is True
        assert second.get("status") == "done"


@pytest.mark.rf("RF-011", title="Logs detallados de búsqueda")
class TestRF011Logging:
    def test_structured_logger_emits_event_extra(self, capsys):
        configure_logging()
        logger = get_logger("acceptance_rf011")
        logger.info(
            "Acceptance probe",
            extra={"event": "acceptance_probe", "search_id": "test-id"},
        )
        out = capsys.readouterr().out
        assert "Acceptance probe" in out
        assert "acceptance_probe" in out
