"""RNF acceptance checks that can be automated without manual checklist."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.acceptance

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parent


@pytest.mark.rf("RNF-001", title="Performance medible (parámetros + informe dataset)")
class TestRNF001Performance:
    def test_tunable_limits_exist(self):
        import search_service
        from scrape_config import SCRAPE_DYNAMIC_MAX_WORKERS, SCRAPE_STATIC_MAX_WORKERS

        assert search_service.SEARCH_MAX_CANDIDATE_URLS >= 1
        assert SCRAPE_STATIC_MAX_WORKERS >= 1
        assert SCRAPE_DYNAMIC_MAX_WORKERS >= 1

    def test_dataset_report_records_timing(self):
        report = REPO_ROOT / "docs" / "dataset-prueba.md"
        if not report.is_file():
            pytest.skip("Falta docs/dataset-prueba.md (correr dataset)")
        text = report.read_text(encoding="utf-8")
        assert "Tiempo promedio" in text or "tiempo" in text.lower()


@pytest.mark.rf("RNF-002", title="Usabilidad web (UI disponible)")
class TestRNF002Usability:
    def test_web_page_or_source_exists(self):
        page = REPO_ROOT / "identificador-web" / "app" / "page.tsx"
        assert page.is_file()
        content = page.read_text(encoding="utf-8")
        assert "Search" in content or "search" in content.lower()

    def test_live_web_serves_ui_if_up(self):
        import requests

        url = os.getenv("INTEGRATION_WEB_URL", "http://127.0.0.1:3000").rstrip("/")
        try:
            response = requests.get(url, timeout=5)
        except requests.RequestException:
            pytest.skip(f"Frontend no disponible en {url}")
        assert response.status_code < 500
        assert "html" in response.headers.get("content-type", "").lower() or response.text


@pytest.mark.rf("RNF-003", title="Confiabilidad ≥ 70 % en dataset")
class TestRNF003Reliability:
    def test_dataset_precision_meets_threshold(self):
        results_path = API_ROOT / "dataset" / "results.json"
        if not results_path.is_file():
            pytest.skip("Falta dataset/results.json — ejecutar scripts/run_dataset.py")
        data = json.loads(results_path.read_text(encoding="utf-8"))
        precision = data.get("precision")
        if precision is None:
            rows = data.get("rows") or []
            if not rows:
                pytest.fail("results.json sin campo precision ni rows")
            correct = sum(
                1
                for row in rows
                if (row.get("evaluation") or {}).get("correct") is True
            )
            precision = correct / len(rows)
        precision_f = float(precision)
        if precision_f > 1:
            precision_f /= 100.0
        assert precision_f >= 0.70


@pytest.mark.rf("RNF-004", title="Mantenibilidad (estructura + docs oficiales)")
class TestRNF004Maintainability:
    def test_docs_and_decoupled_engines_exist(self):
        assert (REPO_ROOT / "docs" / "requerimientos.md").is_file()
        assert (API_ROOT / "search_engines" / "base.py").is_file()
        assert (API_ROOT / "search_engines" / "factory.py").is_file()


@pytest.mark.rf("RNF-005", title="Portabilidad Python 3.11 / stack documentado")
class TestRNF005Portability:
    def test_runtime_is_python_311_plus(self):
        assert sys.version_info >= (3, 11)

    def test_dockerfile_and_readme_exist(self):
        assert (API_ROOT / "Dockerfile").is_file()
        assert (REPO_ROOT / "README.md").is_file()
        assert (REPO_ROOT / "render.yaml").is_file()


@pytest.mark.rf("RNF-006", title="API keys solo en variables de entorno")
class TestRNF006Security:
    def test_env_gitignored_and_example_has_no_real_secret(self):
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        assert ".env" in gitignore
        example = (API_ROOT / ".env.example").read_text(encoding="utf-8")
        assert "SERPAPI_API_KEY" in example
        # Placeholder only — not a 64-char live key pattern as the only value
        for line in example.splitlines():
            if line.startswith("SERPAPI_API_KEY="):
                value = line.split("=", 1)[1].strip()
                assert value in {
                    "tu_clave_serpapi",
                    "",
                    "your_key",
                    "changeme",
                } or "clave" in value.lower() or "key" in value.lower()
                assert len(value) < 40 or "tu_clave" in value
