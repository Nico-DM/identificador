# Plan de pruebas estructurado

Plan alineado a los RF/RNF de la primera entrega actualizados ([requerimientos.md](requerimientos.md)) y al dataset formal ([dataset-prueba.md](dataset-prueba.md)).

---

## 1. Alcance

| Nivel | Objetivo | Ubicación |
|-------|----------|-----------|
| Unitarias | Lógica pura del backend (scoring, parsers, fusión, validación, rate limit) | `identificador-api/tests/` |
| Unitarias frontend | Utilidades y componentes aislados | `identificador-web` (Vitest) |
| Integración | API HTTP + orquestación; proxy Next → FastAPI | `tests/test_routes.py`, smoke, flujos manuales |
| Regresión | Dataset de 10 imágenes | `scripts/run_dataset.py` |
| Aceptación | Criterios RF frente a la aplicación desplegada o local | Checklist §5 |

---

## 2. Pruebas unitarias (backend)

### Cómo ejecutar

```bash
cd identificador-api
source venv/bin/activate
pytest -q
```

### Cobertura objetivo

La devolución exige **≥ 60 %** de cobertura del backend. Medición recomendada:

```bash
pip install -r requirements-dev.txt
python -m pytest --cov=. --cov-report=term-missing
```

El omit de `venv/`, `tests/` y `scripts/` está en `.coveragerc`.

### Módulos cubiertos (mapa)

| Archivo de test | Módulo bajo prueba | RF / RNF |
|-----------------|--------------------|----------|
| `test_publication_scorer.py` | Scoring, plataformas, merge | RF-003, RF-004, RF-007, RF-008 |
| `test_parsers.py` | Parsers Google / Bing / Yandex | RF-002 |
| `test_fusion.py` | RRF y `FusedSearchEngine` | RF-002 |
| `test_search_service.py` | Formato de respuesta, factory | RF-002, RF-005 |
| `test_static_scraper.py` | Extracción estática de fechas | RF-003 |
| `test_image_validation.py` | Validación de URL/imagen | RF-001, RF-006, RF-009 |
| `test_rate_limit.py` | Limitación por IP | RNF-006 (abuso / operación segura) |
| `test_routes.py` | Health, search, deep (estados) | RF-001, RF-005, RF-006 |
| `test_env_util.py` / `test_json_util.py` / `test_exceptions.py` | Utilidades | RNF-004, RNF-006 |
| Logging / eventos (inspección manual o tests de integración) | `logging_config` | RF-011 |

---

## 3. Pruebas de integración

Suite explícita en `identificador-api/tests/integration/`. **No** son unitarias con mocks: pegan a SerpAPI real y, cuando hay servidores vivos, al proxy Next.js.

| Test | Camino | Requisito |
|------|--------|-----------|
| `test_backend_serpapi.py::…Live` | HTTP → FastAPI → SerpAPI → scrape | API en `INTEGRATION_API_URL` + `SERPAPI_API_KEY` |
| `test_backend_serpapi.py::…InProcess` | TestClient → FastAPI → SerpAPI | `SERPAPI_API_KEY` (sin uvicorn aparte) |
| `test_frontend_backend_serpapi.py` | HTTP → Next `/api/*` → FastAPI → SerpAPI | Web + API vivos + `SERPAPI_API_KEY` |

Por defecto `pytest` **excluye** el marker `integration` (`addopts = -m "not integration"`).

### Cómo ejecutar

```bash
# Terminal A: API + web
./scripts/dev.sh

# Terminal B:
./scripts/run_integration.sh
```

Equivalente:

```bash
cd identificador-api
source venv/bin/activate
pytest -m integration tests/integration -v
```

Variables opcionales: `INTEGRATION_API_URL`, `INTEGRATION_WEB_URL`, `INTEGRATION_IMAGE_URL`, `INTEGRATION_TIMEOUT_SECONDS` (default 600).

Si falta la API, el web o la clave, los tests correspondientes hacen **skip**.

---

## 4. Pruebas de regresión (dataset)

```bash
cd identificador-api
python main.py   # otra terminal
python scripts/run_dataset.py
python scripts/generate_dataset_doc.py   # regenera docs/dataset-prueba.md
```

- **Entrada:** `dataset/manifest.json` (10 imágenes: histórica, arte tradicional, meme, stock, digital).
- **Salida:** `dataset/results.json` + informe [dataset-prueba.md](dataset-prueba.md).
- **Criterio de caso correcto:** dominio esperado presente en el top 10 (tras fase dinámica si corre).
- **Métrica de aceptación (RNF-003):** tasa de éxito ≥ **70 %**.
- **Performance (RNF-001):** registrar tiempo promedio; objetivo de diseño ≤ 30 s por consulta.

---

## 5. Pruebas de aceptación (checklist RF / RNF)

| ID | Criterio | Cómo verificar | OK |
|----|----------|----------------|----|
| RF-001 | Acepta URL (y archivo si hay Storage) | UI local/prod | ☐ |
| RF-002 | Búsqueda inversa SerpAPI (`google_reverse_image` ± fallbacks) | Smoke + logs `engine_results` | ☐ |
| RF-003 | Extrae fechas (estático / Selenium) | UI / dataset / logs `*_phase_*` | ☐ |
| RF-004 | Identifica publicación más antigua (ranking) | Primer resultado vs fechas | ☐ |
| RF-005 | Retorna URL + fecha del mejor candidato | API / UI | ☐ |
| RF-006 | Errores de conexión y URLs inválidas | URL mala → mensaje; SerpAPI down → `error` | ☐ |
| RF-007 | Múltiples resultados ordenados | Lista en UI | ☐ |
| RF-008 | Indicadores de confiabilidad | Campos confidence/score | ☐ |
| RF-009 | Formatos JPG/PNG/WebP, etc. | URL/archivo de distintos tipos | ☐ |
| RF-010 | Caché / persistencia | `DATABASE_URL`; repetir misma imagen | ☐ |
| RF-011 | Logs detallados | Consola / Render JSON | ☐ |
| RNF-001 | Performance (objetivo ≤ 30 s) | Dataset / cronómetro | ☐ |
| RNF-002 | Usabilidad web | Flujo completo sin CLI | ☐ |
| RNF-003 | Éxito ≥ 70 % en dataset | `dataset-prueba.md` | ☐ |
| RNF-005 | Python 3.11 / stack documentado | README, Docker | ☐ |
| RNF-006 | Secrets solo en env | `.gitignore`, Render secrets | ☐ |

---

## 6. Criterios de salida para entrega

1. Suite unitaria backend en verde.
2. Informe de dataset actualizado y archivado en `docs/`.
3. Checklist de aceptación completado en entorno de demostración (local o producción).
4. Cobertura backend medida ≥ 60 % (exigencia de la devolución de la 2ª entrega).
