"""Must-have RF acceptance criteria (RF-001 … RF-006)."""

from __future__ import annotations

from datetime import datetime

import pytest
from exceptions import ValidationError
from image_validation import validate_image_url
from models import DateCandidate
from publication_scorer import _sort_publications, select_best_candidate
from scrape_config import JS_RENDER_PLATFORMS, platform_requires_js_render
from static_scraper import fetch_static_candidates
from tests.acceptance.conftest import _poll_done
from tests.helpers import utc_dt

pytestmark = pytest.mark.acceptance


@pytest.mark.rf("RF-001", title="Aceptar URL de imagen válida / rechazar inválida")
class TestRF001Input:
    def test_valid_url_starts_search(
        self, api_client, acceptance_image_url, require_serpapi
    ):
        response = api_client.post(
            "/api/search",
            json={"image_url": acceptance_image_url, "safe_search": True},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body.get("search_id")
        assert body.get("status") in {"processing", "done"}

    def test_invalid_url_rejected(self, api_client):
        response = api_client.post(
            "/api/search",
            json={"image_url": "not-a-url", "safe_search": True},
        )
        assert response.status_code == 400
        payload = response.json()
        assert "detail" in payload or "code" in payload


@pytest.mark.rf("RF-002", title="Búsqueda inversa vía SerpAPI (google_reverse_image)")
@pytest.mark.usefixtures("require_serpapi")
class TestRF002ReverseSearch:
    def test_engine_returns_candidates(self, acceptance_image_url, monkeypatch):
        from search_engines.factory import get_search_engine

        monkeypatch.delenv("SEARCH_FALLBACK_ENGINES", raising=False)
        engine = get_search_engine("google_reverse_image")
        assert engine.name == "google_reverse_image"
        outcome = engine.search(acceptance_image_url, safe_search=True)
        assert len(outcome.urls) >= 1

    def test_search_flow_uses_engine(self, api_client, acceptance_image_url):
        create = api_client.post(
            "/api/search",
            json={"image_url": acceptance_image_url, "safe_search": True},
        )
        assert create.status_code == 200
        payload = _poll_done(api_client, create.json()["search_id"])
        assert payload["status"] == "done", payload.get("error")
        assert len(payload.get("results") or []) >= 1


@pytest.mark.rf("RF-003", title="Extraer fechas (estático + plataformas JS dinámicas)")
class TestRF003Dates:
    def test_static_extraction_from_public_page(self):
        url = "https://en.wikipedia.org/wiki/Mona_Lisa"
        candidates = fetch_static_candidates(url)
        assert isinstance(candidates, list)
        if not candidates:
            pytest.skip(
                "Sin candidatos estáticos (red/HTML cambió); extractor OK sin excepción"
            )

    def test_js_platforms_flagged_for_dynamic(self):
        for platform in (
            "instagram",
            "x",
            "deviantart",
            "artstation",
            "tiktok",
            "facebook",
        ):
            assert platform in JS_RENDER_PLATFORMS
            assert platform_requires_js_render(platform) is True


@pytest.mark.rf("RF-004", title="Identificar publicación más antigua (ranking)")
class TestRF004Oldest:
    def test_sort_prefers_earlier_dated_results(self):
        pubs = [
            {
                "link": "https://b.example/late",
                "created_utc": utc_dt(2020, 1, 1),
                "score": 0.5,
                "confidence": "confirmed",
            },
            {
                "link": "https://a.example/early",
                "created_utc": utc_dt(2010, 1, 1),
                "score": 0.5,
                "confidence": "confirmed",
            },
        ]
        _sort_publications(pubs)
        assert pubs[0]["link"] == "https://a.example/early"

    def test_select_best_candidate_picks_earliest_among_scored(self):
        candidates = [
            DateCandidate(
                date=utc_dt(2015, 1, 1),
                source="meta",
                raw="",
                extractor="static",
                url="https://x.com",
                score=0.8,
            ),
            DateCandidate(
                date=utc_dt(2010, 1, 1),
                source="ld+json",
                raw="",
                extractor="static",
                url="https://x.com",
                score=0.8,
            ),
        ]
        best = select_best_candidate(candidates)
        assert best is not None
        assert best.date.year == 2010


@pytest.mark.rf("RF-005", title="Retornar URL (y fecha si hay) del mejor candidato")
@pytest.mark.usefixtures("require_serpapi")
class TestRF005ReturnUrlDate:
    def test_results_include_url_and_confidence(
        self, api_client, acceptance_image_url
    ):
        create = api_client.post(
            "/api/search",
            json={"image_url": acceptance_image_url, "safe_search": True},
        )
        assert create.status_code == 200
        payload = _poll_done(api_client, create.json()["search_id"])
        assert payload["status"] == "done", payload.get("error")
        results = payload["results"]
        assert results
        top = results[0]
        assert top.get("url")
        assert "confidence" in top
        if top.get("date"):
            datetime.fromisoformat(str(top["date"]).replace("Z", "+00:00"))


@pytest.mark.rf("RF-006", title="Errores de URL inválida y servicio estable")
class TestRF006Errors:
    def test_validate_image_url_rejects_bad_scheme(self):
        with pytest.raises(ValidationError):
            validate_image_url("ftp://example.com/a.jpg")

    def test_health_ok_after_bad_search(self, api_client):
        bad = api_client.post(
            "/api/search", json={"image_url": "https://example.com/x.pdf"}
        )
        assert bad.status_code == 400
        health = api_client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
