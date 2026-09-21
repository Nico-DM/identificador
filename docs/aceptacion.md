# Informe de pruebas de aceptación

Generado automáticamente: 2026-09-21T23:04:40.536275+00:00

Cada fila corresponde a un criterio RF/RNF ejercitado por `pytest -m acceptance` (ver `identificador-api/tests/acceptance/`).

| ID | Criterio | Resultado | Test | Detalle |
|----|----------|-----------|------|---------|
| RF-001 | Aceptar URL de imagen válida / rechazar inválida | **PASS** | `tests/acceptance/test_rf_must.py::TestRF001Input::test_valid_url_starts_search` |  |
| RF-002 | Búsqueda inversa vía SerpAPI (google_reverse_image) | **PASS** | `tests/acceptance/test_rf_must.py::TestRF002ReverseSearch::test_engine_returns_candidates` |  |
| RF-003 | Extraer fechas (estático + plataformas JS dinámicas) | **PASS** | `tests/acceptance/test_rf_must.py::TestRF003Dates::test_static_extraction_from_public_page` |  |
| RF-004 | Identificar publicación más antigua (ranking) | **PASS** | `tests/acceptance/test_rf_must.py::TestRF004Oldest::test_sort_prefers_earlier_dated_results` |  |
| RF-005 | Retornar URL (y fecha si hay) del mejor candidato | **PASS** | `tests/acceptance/test_rf_must.py::TestRF005ReturnUrlDate::test_results_include_url_and_confidence` |  |
| RF-006 | Errores de URL inválida y servicio estable | **PASS** | `tests/acceptance/test_rf_must.py::TestRF006Errors::test_validate_image_url_rejects_bad_scheme` |  |
| RF-007 | Múltiples resultados ordenados | **PASS** | `tests/acceptance/test_rf_should_could.py::TestRF007MultipleResults::test_api_returns_list_of_candidates` |  |
| RF-008 | Indicadores de confiabilidad | **PASS** | `tests/acceptance/test_rf_should_could.py::TestRF008Confidence::test_confidence_levels_from_score` |  |
| RF-009 | Múltiples formatos de imagen | **PASS** | `tests/acceptance/test_rf_should_could.py::TestRF009Formats::test_upload_validation_jpg_png_webp` |  |
| RF-010 | Caché de resultados para consultas repetidas | **PASS** | `tests/acceptance/test_rf_should_could.py::TestRF010Cache::test_memory_analysis_cache_roundtrip` |  |
| RF-011 | Logs detallados de búsqueda | **PASS** | `tests/acceptance/test_rf_should_could.py::TestRF011Logging::test_structured_logger_emits_event_extra` |  |
| RNF-001 | Performance medible (parámetros + informe dataset) | **PASS** | `tests/acceptance/test_rnf.py::TestRNF001Performance::test_tunable_limits_exist` |  |
| RNF-002 | Usabilidad web (UI disponible) | **PASS** | `tests/acceptance/test_rnf.py::TestRNF002Usability::test_web_page_or_source_exists` |  |
| RNF-003 | Confiabilidad ≥ 70 % en dataset | **FAIL** | `tests/acceptance/test_rnf.py::TestRNF003Reliability::test_dataset_precision_meets_threshold` | tests/acceptance/test_rnf.py:77: in test_dataset_precision_meets_threshold     assert precision_f >= 0.70 E   assert 0.5 >= 0.7 |
| RNF-004 | Mantenibilidad (estructura + docs oficiales) | **PASS** | `tests/acceptance/test_rnf.py::TestRNF004Maintainability::test_docs_and_decoupled_engines_exist` |  |
| RNF-005 | Portabilidad Python 3.11 / stack documentado | **PASS** | `tests/acceptance/test_rnf.py::TestRNF005Portability::test_runtime_is_python_311_plus` |  |
| RNF-006 | API keys solo en variables de entorno | **PASS** | `tests/acceptance/test_rnf.py::TestRNF006Security::test_env_gitignored_and_example_has_no_real_secret` |  |

**Resumen:** 16 PASS · 1 FAIL · 0 SKIP (exitstatus=1)

Cómo regenerar:

```bash
./scripts/run_acceptance.sh
```

