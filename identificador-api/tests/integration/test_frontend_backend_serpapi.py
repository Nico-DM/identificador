"""
Integración frontend → backend → API externa (SerpAPI).

Ejercita el proxy Next.js (`/api/search`, `/api/results/...`) hacia FastAPI,
que a su vez consulta SerpAPI. Requiere web + API vivos.

  INTEGRATION_WEB_URL=http://127.0.0.1:3000
  INTEGRATION_API_URL=http://127.0.0.1:8000
  pytest -m integration tests/integration/test_frontend_backend_serpapi.py
"""

from __future__ import annotations

import os

import pytest
import requests
from tests.integration.conftest import poll_until_terminal

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures("require_serpapi", "require_live_api", "require_live_web")
class TestFrontendBackendExternalApi:
    def test_proxy_search_and_poll(
        self,
        web_base_url: str,
        api_base_url: str,
        image_url: str,
    ):
        # Sanity: backend healthy before blaming the proxy.
        assert requests.get(f"{api_base_url}/health", timeout=5).status_code == 200

        create = requests.post(
            f"{web_base_url}/api/search",
            json={"image_url": image_url, "safe_search": True},
            headers={"content-type": "application/json"},
            timeout=60,
        )
        assert create.status_code == 200, create.text
        body = create.json()
        search_id = body.get("search_id")
        assert search_id, body
        assert body.get("status") in {"processing", "done", "static_done"}

        payload = poll_until_terminal(
            f"{web_base_url}/api/results/{search_id}",
            timeout_seconds=float(os.getenv("INTEGRATION_TIMEOUT_SECONDS", "600")),
        )

        assert payload["status"] == "done", payload.get("error")
        assert isinstance(payload.get("results"), list)
        assert len(payload["results"]) >= 1
        assert payload["results"][0].get("url")

    def test_proxy_rejects_invalid_url_like_frontend(self, web_base_url: str):
        response = requests.post(
            f"{web_base_url}/api/search",
            json={"image_url": "https://example.com/file.pdf"},
            headers={"content-type": "application/json"},
            timeout=30,
        )
        assert response.status_code == 400
        detail = response.json()
        assert "detail" in detail or "error" in detail
