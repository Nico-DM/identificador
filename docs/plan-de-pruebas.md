# Plan de pruebas estructurado

Plan alineado a los RF/RNF ([requerimientos.md](requerimientos.md)) y al dataset formal ([dataset-prueba.md](dataset-prueba.md)).

---

## 1. Alcance

| Nivel              | Objetivo                                                                   | Ubicación                                      |
| ------------------ | -------------------------------------------------------------------------- | ---------------------------------------------- |
| Unitarias          | Lógica pura del backend (scoring, parsers, fusión, validación, rate limit) | `identificador-api/tests/`                     |
| Unitarias frontend | Utilidades y componentes aislados                                          | `identificador-web` (Vitest)                   |
| Integración        | API HTTP + orquestación; proxy Next → FastAPI                              | `tests/test_routes.py`, smoke, flujos manuales |
| Regresión          | Dataset de 10 imágenes                                                     | `scripts/run_dataset.py`                       |
| Aceptación         | Criterios RF frente a la aplicación desplegada o local                     | Checklist §5                                   |

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
pip install pytest-cov
pytest --cov=. --cov-report=term-missing \
  --cov-omit='venv/*,tests/*,scripts/*'
```

### Módulos cubiertos (mapa)

| Archivo de test                                                 | Módulo bajo prueba             | RF / RNF               |
| --------------------------------------------------------------- | ------------------------------ | ---------------------- |
| `test_publication_scorer.py`                                    | Scoring, plataformas, merge    | RF-005, RF-007, RF-008 |
| `test_parsers.py`                                               | Parsers Google / Bing / Yandex | RF-002, RF-011         |
| `test_fusion.py`                                                | RRF y `FusedSearchEngine`      | RF-011                 |
| `test_search_service.py`                                        | Formato de respuesta, factory  | RF-002, RF-009         |
| `test_static_scraper.py`                                        | Extracción estática de fechas  | RF-004, RF-007         |
| `test_image_validation.py`                                      | Validación de URL/imagen       | RF-001                 |
| `test_rate_limit.py`                                            | Limitación por IP              | RNF-004                |
| `test_routes.py`                                                | Health, search, deep (estados) | RF-009, RF-008         |
| `test_env_util.py` / `test_json_util.py` / `test_exceptions.py` | Utilidades                     | RNF-005, RNF-006       |

---

## 3. Pruebas de integración

### 3.1 Backend aislado (smoke)

```bash
# API en marcha en :8000
python scripts/smoke_test.py \
  --image-url "https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Color_of_Friendship.jpg/960px-Color_of_Friendship.jpg"
```

Verifica: `POST /api/search` → polling hasta `done` (incluye auto-deep si aplica).

### 3.2 Frontend ↔ backend

1. `./scripts/dev.sh` (o API + `npm run dev`).
2. Pegar URL de imagen y/o subir archivo.
3. Confirmar progreso, resultados y ausencia de errores de proxy.

### 3.3 API externa (SerpAPI)

Requiere `SERPAPI_API_KEY` válida. El smoke y el dataset ejercitan el camino real motor → scrape. Fallos de red/cuota deben aparecer en logs estructurados (`event=search_failed` / errores de engine).

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
- **Métrica de aceptación (RNF-001):** precisión ≥ 70 %.

---

## 5. Pruebas de aceptación (checklist RF)

| ID      | Criterio                               | Cómo verificar                                          | OK  |
| ------- | -------------------------------------- | ------------------------------------------------------- | --- |
| RF-001  | URL y (si hay storage) archivo         | UI local/prod                                           | ☐   |
| RF-002  | Búsqueda inversa con motor configurado | Smoke + logs `engine_results`                           | ☐   |
| RF-003  | Límite de candidatos                   | Inspeccionar `SEARCH_MAX_CANDIDATE_URLS` / logs         | ☐   |
| RF-004  | Fechas en resultados                   | UI / dataset                                            | ☐   |
| RF-005  | Orden por relevancia/fecha             | Comparar scores en UI                                   | ☐   |
| RF-006  | Polling y listado                      | UI                                                      | ☐   |
| RF-007  | Fase estática                          | Logs `static_phase_*`                                   | ☐   |
| RF-008  | Selenium auto en JS / baja confianza   | Logs `deep_search_auto_start`; Docker Render            | ☐   |
| RF-009  | Estados `processing`→`done`            | Network tab / smoke                                     | ☐   |
| RF-010  | Persistencia con `DATABASE_URL`        | `/health` → supabase; reinicio no pierde caché reciente | ☐   |
| RF-011  | Fallbacks                              | Configurar `SEARCH_FALLBACK_ENGINES`; logs de fusión    | ☐   |
| RNF-001 | Precisión dataset                      | `dataset-prueba.md`                                     | ☐   |
| RNF-004 | Rate limit                             | Exceder cuota horaria → 429                             | ☐   |
| RNF-006 | Logs                                   | Render / consola JSON                                   | ☐   |

---

## 6. Criterios de salida para entrega

1. Suite unitaria backend en verde.
2. Informe de dataset actualizado y archivado en `docs/`.
3. Checklist de aceptación completado en entorno de demostración (local o producción).
4. Cobertura backend medida ≥ 60 % (o justificación documentada si el omit set se acota a código de producto).
