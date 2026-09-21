"""Acceptance tests: map each RF/RNF criterion to an executable check."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parent
load_dotenv(API_ROOT / ".env")

ACCEPTANCE_REPORT = REPO_ROOT / "docs" / "aceptacion.md"

# Populated by hooks; written at session end.
_ACCEPTANCE_ROWS: list[dict[str, str]] = []


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "acceptance: validates RF/RNF acceptance criteria (pytest -m acceptance)",
    )
    config.addinivalue_line(
        "markers",
        "rf(id): requirement id under acceptance (e.g. RF-001)",
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[Any]):
    outcome = yield
    report = outcome.get_result()
    if report.when not in {"setup", "call"}:
        return
    rf_marker = item.get_closest_marker("rf")
    if rf_marker is None:
        return
    # Prefer call outcome; use setup only when the test was skipped in setup.
    if report.when == "setup" and not report.skipped:
        return

    req_id = str(rf_marker.args[0]) if rf_marker.args else "UNKNOWN"
    title = rf_marker.kwargs.get("title") or item.name
    if report.skipped:
        status = "SKIP"
        detail = str(report.longrepr)[:200] if report.longrepr else ""
    elif report.failed:
        status = "FAIL"
        detail = str(report.longrepr)[:200] if report.longrepr else ""
    elif report.passed and report.when == "call":
        status = "PASS"
        detail = ""
    else:
        return

    _ACCEPTANCE_ROWS.append(
        {
            "id": req_id,
            "title": str(title),
            "status": status,
            "node": item.nodeid,
            "detail": detail.replace("\n", " "),
        }
    )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if not _ACCEPTANCE_ROWS:
        return
    # Keep last result per requirement id (tests may share an RF).
    by_id: dict[str, dict[str, str]] = {}
    for row in _ACCEPTANCE_ROWS:
        prev = by_id.get(row["id"])
        # Prefer FAIL over SKIP over PASS when aggregating.
        rank = {"FAIL": 0, "SKIP": 1, "PASS": 2}
        if prev is None or rank[row["status"]] < rank[prev["status"]]:
            by_id[row["id"]] = row

    lines = [
        "# Informe de pruebas de aceptación",
        "",
        f"Generado automáticamente: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Cada fila corresponde a un criterio RF/RNF ejercitado por `pytest -m acceptance` (ver `identificador-api/tests/acceptance/`).",
        "",
        "| ID | Criterio | Resultado | Test | Detalle |",
        "|----|----------|-----------|------|---------|",
    ]
    for req_id in sorted(by_id.keys()):
        row = by_id[req_id]
        detail = row["detail"].replace("|", "\\|")
        lines.append(
            f"| {row['id']} | {row['title']} | **{row['status']}** | "
            f"`{row['node']}` | {detail} |"
        )

    passed = sum(1 for r in by_id.values() if r["status"] == "PASS")
    failed = sum(1 for r in by_id.values() if r["status"] == "FAIL")
    skipped = sum(1 for r in by_id.values() if r["status"] == "SKIP")
    lines.extend(
        [
            "",
            f"**Resumen:** {passed} PASS · {failed} FAIL · {skipped} SKIP (exitstatus={exitstatus})",
            "",
            "Cómo regenerar:",
            "",
            "```bash",
            "./scripts/run_acceptance.sh",
            "```",
            "",
        ]
    )
    ACCEPTANCE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    ACCEPTANCE_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture(scope="session")
def acceptance_image_url() -> str:
    return os.getenv(
        "ACCEPTANCE_IMAGE_URL",
        os.getenv(
            "INTEGRATION_IMAGE_URL",
            "https://upload.wikimedia.org/wikipedia/commons/thumb/"
            "1/10/Color_of_Friendship.jpg/960px-Color_of_Friendship.jpg",
        ),
    )


@pytest.fixture(scope="session")
def require_serpapi() -> None:
    key = (os.getenv("SERPAPI_API_KEY") or "").strip()
    if not key or key in {"tu_clave_serpapi", "changeme", "your_key"}:
        pytest.skip("SERPAPI_API_KEY real requerida para este criterio de aceptación")


@pytest.fixture
def api_client(monkeypatch: pytest.MonkeyPatch):
    """In-process FastAPI client with fast scrape settings."""
    monkeypatch.setenv("DISABLE_DATABASE", "1")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("SCRAPE_DYNAMIC_ENABLED", "false")
    monkeypatch.setenv("SEARCH_MAX_CANDIDATE_URLS", "8")

    import scrape_config
    import search_service

    monkeypatch.setattr(scrape_config, "SCRAPE_DYNAMIC_ENABLED", False)
    monkeypatch.setattr(search_service, "SCRAPE_DYNAMIC_ENABLED", False)
    monkeypatch.setattr(search_service, "SEARCH_MAX_CANDIDATE_URLS", 8)

    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as client:
        yield client


def _poll_done(client, search_id: str, *, timeout_s: int = 300) -> dict:
    import time

    deadline = time.monotonic() + timeout_s
    last: dict | None = None
    while time.monotonic() < deadline:
        response = client.get(f"/api/results/{search_id}")
        assert response.status_code == 200
        last = response.json()
        assert last is not None
        if last.get("status") in {"done", "error"}:
            return last
        time.sleep(1)
    raise TimeoutError(f"Aceptación: timeout esperando done; último={last}")
