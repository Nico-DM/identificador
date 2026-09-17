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
pip install pytest-cov
pytest --cov=. --cov-report=term-missing \
  --cov-omit='venv/*,tests/*,scripts/*'
```

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
3. Confirmar progreso, resultados y ausencia de errores de proxy (RNF-002).

### 3.3 API externa (SerpAPI)

Requiere `SERPAPI_API_KEY` válida (RNF-006). El smoke y el dataset ejercitan el camino real motor → scrape. Fallos de red/cuota deben aparecer en logs estructurados (RF-006, RF-011).

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
