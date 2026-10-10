"""Fixtures for live integration tests (backend ↔ SerpAPI ↔ optional frontend)."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]  # identificador-api/
load_dotenv(ROOT / ".env")

# Stable public image used across smoke/dataset.
DEFAULT_IMAGE_URL = (
    "https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/6c5329df-ff97-41d6-a1c0-306053a68d43/dhk2ysn-a588ec66-1dab-4ff0-abe6-4d52c885aa81.png/v1/fill/w_892,h_896,q_70,strp/dnd_gunslinger_character_by_qoentari_dhk2ysn-pre.jpg?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOjdlMGQxODg5ODIyNjQzNzNhNWYwZDQxNWVhMGQyNmUwIiwiaXNzIjoidXJuOmFwcDo3ZTBkMTg4OTgyMjY0MzczYTVmMGQ0MTVlYTBkMjZlMCIsIm9iaiI6W1t7ImhlaWdodCI6Ijw9MTI4NSIsInBhdGgiOiIvZi82YzUzMjlkZi1mZjk3LTQxZDYtYTFjMC0zMDYwNTNhNjhkNDMvZGhrMnlzbi1hNTg4ZWM2Ni0xZGFiLTRmZjAtYWJlNi00ZDUyYzg4NWFhODEucG5nIiwid2lkdGgiOiI8PTEyODAifV1dLCJhdWQiOlsidXJuOnNlcnZpY2U6aW1hZ2Uub3BlcmF0aW9ucyJdfQ.PwTiCHcSP0pFDIcSYWSI0f0CWmDBiME67TItzPygM6g"
)

TERMINAL = frozenset({"done", "error"})


def _serpapi_configured() -> bool:
    key = (os.getenv("SERPAPI_API_KEY") or "").strip()
    return bool(key) and key not in {"tu_clave_serpapi", "changeme", "your_key"}


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: hits live backend/SerpAPI/frontend (opt-in via -m integration)",
    )


@pytest.fixture(scope="session")
def image_url() -> str:
    return os.getenv("INTEGRATION_IMAGE_URL", DEFAULT_IMAGE_URL)


@pytest.fixture(scope="session")
def api_base_url() -> str:
    return os.getenv("INTEGRATION_API_URL", "http://127.0.0.1:8000").rstrip("/")


@pytest.fixture(scope="session")
def web_base_url() -> str:
    return os.getenv("INTEGRATION_WEB_URL", "http://127.0.0.1:3000").rstrip("/")


@pytest.fixture(scope="session")
def require_serpapi() -> None:
    if not _serpapi_configured():
        pytest.skip(
            "SERPAPI_API_KEY real requerida para integración con API externa"
        )


@pytest.fixture(scope="session")
def require_live_api(api_base_url: str) -> None:
    try:
        response = requests.get(f"{api_base_url}/health", timeout=5)
    except requests.RequestException as exc:
        pytest.skip(f"Backend no disponible en {api_base_url}: {exc}")
    if response.status_code != 200:
        pytest.skip(
            f"Backend /health devolvió HTTP {response.status_code} en {api_base_url}"
        )


@pytest.fixture(scope="session")
def require_live_web(web_base_url: str) -> None:
    try:
        response = requests.get(web_base_url, timeout=5)
    except requests.RequestException as exc:
        pytest.skip(f"Frontend no disponible en {web_base_url}: {exc}")
    if response.status_code >= 500:
        pytest.skip(
            f"Frontend devolvió HTTP {response.status_code} en {web_base_url}"
        )


def poll_until_terminal(
    results_url: str,
    *,
    timeout_seconds: float,
    poll_interval: float = 2.0,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last: dict | None = None
    while time.monotonic() < deadline:
        response = requests.get(results_url, timeout=30)
        response.raise_for_status()
        payload = response.json()
        assert isinstance(payload, dict)
        last = payload
        status = last.get("status")
        if status in TERMINAL:
            return last
        time.sleep(poll_interval)
    raise TimeoutError(
        f"Timeout ({timeout_seconds:.0f}s) esperando done/error; último={last}"
    )


@pytest.fixture
def fast_scrape_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Speed up in-process TestClient runs (no Selenium)."""
    monkeypatch.setenv("DISABLE_DATABASE", "1")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("SCRAPE_DYNAMIC_ENABLED", "false")
    monkeypatch.setenv("SEARCH_MAX_CANDIDATE_URLS", "5")
    # Constants already imported in modules — patch where used.
    import scrape_config
    import search_service

    monkeypatch.setattr(scrape_config, "SCRAPE_DYNAMIC_ENABLED", False)
    monkeypatch.setattr(search_service, "SCRAPE_DYNAMIC_ENABLED", False)
    monkeypatch.setattr(search_service, "SEARCH_MAX_CANDIDATE_URLS", 5)
    yield
