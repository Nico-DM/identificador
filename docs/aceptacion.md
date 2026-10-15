# Informe de pruebas de aceptación

Generado automáticamente: 2026-10-15T04:43:46.358598+00:00

Cada fila es un test de `pytest -m acceptance`; un mismo criterio RF/RNF puede tener varias filas.

| ID | Criterio | Resultado | Test |
|----|----------|-----------|------|
| RF-001 | Aceptar URL de imagen válida / rechazar inválida | **PASS** | `tests/acceptance/test_rf_must.py::TestRF001Input::test_invalid_url_rejected` |
| RF-001 | Aceptar URL de imagen válida / rechazar inválida | **PASS** | `tests/acceptance/test_rf_must.py::TestRF001Input::test_valid_url_starts_search` |
| RF-002 | Búsqueda inversa vía SerpAPI (google_reverse_image) | **PASS** | `tests/acceptance/test_rf_must.py::TestRF002ReverseSearch::test_engine_returns_candidates` |
| RF-002 | Búsqueda inversa vía SerpAPI (google_reverse_image) | **PASS** | `tests/acceptance/test_rf_must.py::TestRF002ReverseSearch::test_search_flow_uses_engine` |
| RF-003 | Extraer fechas (estático + plataformas JS dinámicas) | **PASS** | `tests/acceptance/test_rf_must.py::TestRF003Dates::test_js_platforms_flagged_for_dynamic` |
| RF-003 | Extraer fechas (estático + plataformas JS dinámicas) | **PASS** | `tests/acceptance/test_rf_must.py::TestRF003Dates::test_static_extraction_from_public_page` |
| RF-004 | Identificar publicación más antigua (ranking) | **PASS** | `tests/acceptance/test_rf_must.py::TestRF004Oldest::test_select_best_candidate_picks_earliest_among_scored` |
| RF-004 | Identificar publicación más antigua (ranking) | **PASS** | `tests/acceptance/test_rf_must.py::TestRF004Oldest::test_sort_prefers_earlier_dated_results` |
| RF-005 | Retornar URL (y fecha si hay) del mejor candidato | **PASS** | `tests/acceptance/test_rf_must.py::TestRF005ReturnUrlDate::test_results_include_url_and_confidence` |
| RF-006 | Errores de URL inválida y servicio estable | **PASS** | `tests/acceptance/test_rf_must.py::TestRF006Errors::test_health_ok_after_bad_search` |
| RF-006 | Errores de URL inválida y servicio estable | **PASS** | `tests/acceptance/test_rf_must.py::TestRF006Errors::test_validate_image_url_rejects_bad_scheme` |
| RF-007 | Múltiples resultados ordenados | **PASS** | `tests/acceptance/test_rf_should_could.py::TestRF007MultipleResults::test_api_returns_list_of_candidates` |
| RF-008 | Indicadores de confiabilidad | **PASS** | `tests/acceptance/test_rf_should_could.py::TestRF008Confidence::test_confidence_levels_from_score` |
| RF-008 | Indicadores de confiabilidad | **PASS** | `tests/acceptance/test_rf_should_could.py::TestRF008Confidence::test_publication_exposes_confidence` |
| RF-009 | Múltiples formatos de imagen | **PASS** | `tests/acceptance/test_rf_should_could.py::TestRF009Formats::test_upload_validation_jpg_png_webp` |
| RF-009 | Múltiples formatos de imagen | **PASS** | `tests/acceptance/test_rf_should_could.py::TestRF009Formats::test_url_extensions_accepted` |
| RF-010 | Caché de resultados para consultas repetidas | **PASS** | `tests/acceptance/test_rf_should_could.py::TestRF010Cache::test_memory_analysis_cache_roundtrip` |
| RF-010 | Caché de resultados para consultas repetidas | **PASS** | `tests/acceptance/test_rf_should_could.py::TestRF010Cache::test_second_search_can_hit_cache` |
| RF-011 | Logs detallados de búsqueda | **PASS** | `tests/acceptance/test_rf_should_could.py::TestRF011Logging::test_structured_logger_emits_event_extra` |
| RNF-001 | Performance ≤ 30 s (parámetros + informe dataset) | **PASS** | `tests/acceptance/test_rnf.py::TestRNF001Performance::test_average_response_under_30s` |
| RNF-001 | Performance ≤ 30 s (parámetros + informe dataset) | **PASS** | `tests/acceptance/test_rnf.py::TestRNF001Performance::test_dataset_report_records_timing` |
| RNF-001 | Performance ≤ 30 s (parámetros + informe dataset) | **PASS** | `tests/acceptance/test_rnf.py::TestRNF001Performance::test_tunable_limits_exist` |
| RNF-002 | Usabilidad web (UI disponible) | **PASS** | `tests/acceptance/test_rnf.py::TestRNF002Usability::test_live_web_serves_ui_if_up` |
| RNF-002 | Usabilidad web (UI disponible) | **PASS** | `tests/acceptance/test_rnf.py::TestRNF002Usability::test_web_page_or_source_exists` |
| RNF-003 | Confiabilidad ≥ 70 % en dataset | **PASS** | `tests/acceptance/test_rnf.py::TestRNF003Reliability::test_dataset_precision_meets_threshold` |
| RNF-004 | Mantenibilidad (estructura + docs oficiales) | **PASS** | `tests/acceptance/test_rnf.py::TestRNF004Maintainability::test_docs_and_decoupled_engines_exist` |
| RNF-005 | Portabilidad Python 3.11 / stack documentado | **PASS** | `tests/acceptance/test_rnf.py::TestRNF005Portability::test_dockerfile_and_readme_exist` |
| RNF-005 | Portabilidad Python 3.11 / stack documentado | **PASS** | `tests/acceptance/test_rnf.py::TestRNF005Portability::test_runtime_is_python_311_plus` |
| RNF-006 | API keys solo en variables de entorno | **PASS** | `tests/acceptance/test_rnf.py::TestRNF006Security::test_env_gitignored_and_example_has_no_real_secret` |

**Resumen (por criterio):** 17 PASS · 0 FAIL · 0 SKIP · 29 tests (exitstatus=0)

Cómo regenerar:

```bash
./scripts/run_acceptance.sh
```

