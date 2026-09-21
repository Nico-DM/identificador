"""
Integración backend ↔ API externa (SerpAPI).

Cubre el camino real: HTTP API → search_service → SerpAPI → scrape estático.
No mockea el motor ni el HTTP de SerpAPI.

Ejecutar (API en proceso aparte, típico):
  RUN vía scripts/run_integration.sh
  o: pytest -m integration tests/integration/test_backend_serpapi.py
"""

from __future__ import annotations

import os

import pytest
import requests
from tests.integration.conftest import poll_until_terminal

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures("require_serpapi", "require_live_api")
class TestBackendExternalApiLive:
    def test_search_poll_completes_with_serpapi(
        self,
        api_base_url: str,
        image_url: str,
    ):
        create = requests.post(
            f"{api_base_url}/api/search",
            json={"image_url": image_url, "safe_search": True},
            timeout=60,
        )
        assert create.status_code == 200, create.text
        body = create.json()
        search_id = body["search_id"]
        assert body["status"] in {"processing", "done"}
        assert search_id

        payload = poll_until_terminal(
            f"{api_base_url}/api/results/{search_id}",
            timeout_seconds=float(os.getenv("INTEGRATION_TIMEOUT_SECONDS", "600")),
        )

        assert payload["search_id"] == search_id
        assert payload["status"] == "done", payload.get("error")
        assert isinstance(payload.get("results"), list)
        assert len(payload["results"]) >= 1
        first = payload["results"][0]
        assert first.get("url")


@pytest.mark.usefixtures("require_serpapi", "fast_scrape_env")
class TestBackendExternalApiInProcess:
    """Same stack without a separate uvicorn process (TestClient + SerpAPI real)."""

    def test_search_via_testclient(self, image_url: str):
        from fastapi.testclient import TestClient
        from main import app

        with TestClient(app) as client:
            health = client.get("/health")
            assert health.status_code == 200

            create = client.post(
                "/api/search",
                json={"image_url": image_url, "safe_search": True},
            )
            assert create.status_code == 200, create.text
            search_id = create.json()["search_id"]

            # TestClient drains background tasks before returning from POST when
            # using the context manager; still poll in case of race / cache path.
            deadline_payload = None
            for _ in range(120):
                results = client.get(f"/api/results/{search_id}")
                assert results.status_code == 200
                deadline_payload = results.json()
                if deadline_payload.get("status") in {"done", "error"}:
                    break
                import time

                time.sleep(1)

            assert deadline_payload is not None
            assert deadline_payload["status"] == "done", deadline_payload.get("error")
            assert len(deadline_payload.get("results") or []) >= 1
