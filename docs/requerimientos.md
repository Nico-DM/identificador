# Requerimientos funcionales y no funcionales

Documento formal de la PPS *Identificador de Artistas*.

---

## Evolución respecto de la primera entrega

| Aspecto | Primera entrega | Entrega actual |
|---------|-----------------|----------------|
| Entrada | URL de imagen (CLI) | URL y, si hay Storage, archivo (web) |
| Búsqueda inversa (RF-002) | Google Lens vía SerpAPI | Google Reverse Image vía SerpAPI (Lens degradado; ver [contingencia](contingencia-google-lens.md)); fallbacks Bing/Yandex |
| Interfaz (RNF-002) | CLI con `--help` | Interfaz web (Next.js) |
| Runtime (RNF-005) | Python 3.8+ | Backend Python **3.11** (FastAPI); frontend Node/Next.js |
| Fechas / scrapers | Extracción en CLI | Estático (BeautifulSoup) + dinámico (Selenium) automático en sitios JS |
| Caché / logs (RF-010, RF-011) | Deseables | Implementados (Postgres/Supabase + logs estructurados) |

---

## 1. Requerimientos funcionales

### Requerimientos principales (Must Have)

#### RF-001 — Aceptar URLs de imágenes como entrada
| | |
|--|--|
| **Descripción (1ª entrega)** | El sistema debe aceptar URLs de imágenes como entrada. |
| **Descripción actual** | El sistema acepta una URL pública `http`/`https` de imagen. Como extensión del mismo flujo, también acepta **subida de archivo** cuando Supabase Storage está configurado. |
| **Prioridad** | Must |
| **Criterios de aceptación** | (1) URL de imagen válida inicia una búsqueda. (2) URLs no-imagen o esquema inválido se rechazan. (3) Con Storage configurado, un archivo de imagen válido inicia la misma búsqueda. |
| **Trazabilidad** | `routes/search.py`, `image_validation.py`, `storage.py`; UI `components/search/`, `hooks/useSearch.ts` |

#### RF-002 — Búsqueda inversa de imágenes vía SerpAPI
| | |
|--|--|
| **Descripción (1ª entrega)** | El sistema debe realizar búsqueda inversa de imágenes usando Google Lens vía SerpAPI. |
| **Descripción actual** | El sistema realiza búsqueda inversa vía SerpAPI con motor configurable. El **primario** es `google_reverse_image` (reemplazo de Lens tras su degradación semántica). Opcionalmente fusiona Bing y/o Yandex (`SEARCH_FALLBACK_ENGINES`). La lógica de negocio se desacopla del proveedor (Strategy). |
| **Prioridad** | Must |
| **Criterios de aceptación** | (1) Con `SERPAPI_API_KEY` válida se obtienen URLs candidatas. (2) `SEARCH_ENGINE` selecciona el adaptador. (3) Fallos del proveedor se registran y se exponen como error de búsqueda. |
| **Trazabilidad** | `search_engines/` (`base`, `factory`, `google_reverse_image`, `fused_engine`, …); `search_service.py` |
| **Nota** | Justificación del cambio de motor: [alternativas-tecnologicas.md](alternativas-tecnologicas.md), [contingencia-google-lens.md](contingencia-google-lens.md). |

#### RF-003 — Extraer fechas de publicación
| | |
|--|--|
| **Descripción** | El sistema debe extraer fechas de publicación de los resultados encontrados. |
| **Prioridad** | Must |
| **Criterios de aceptación** | (1) Fase estática sobre HTML (metadatos, `time`, JSON-LD, etc.). (2) Fase dinámica (Selenium) por defecto en plataformas JS (Instagram, X, ArtStation, DeviantArt, TikTok, Facebook) y en candidatos de baja confianza estática, salvo `SCRAPE_DYNAMIC_ENABLED=false`. |
| **Trazabilidad** | `static_scraper.py`, `dynamic_scraper.py`, `publication_scorer.py`, `scrape_config.py` |

#### RF-004 — Identificar la publicación más antigua
| | |
|--|--|
| **Descripción** | El sistema debe identificar la publicación más antigua entre los candidatos con fecha usable. |
| **Prioridad** | Must |
| **Criterios de aceptación** | Los candidatos se puntúan y ordenan de modo que las fechas más tempranas y confiables queden priorizadas; el primer resultado es la mejor estimación de origen bajo el modelo de scoring actual. |
| **Trazabilidad** | `publication_scorer.py` |

#### RF-005 — Retornar URL de la publicación original con su fecha
| | |
|--|--|
| **Descripción** | El sistema debe retornar la URL de la publicación original (mejor candidato) con su fecha. |
| **Prioridad** | Must |
| **Criterios de aceptación** | La respuesta (API y UI) incluye al menos un resultado destacado con `url` y `date` cuando la extracción fue exitosa; si no hay fecha, se indica confianza `pending` / ausencia de fecha de forma explícita. |
| **Trazabilidad** | `search_service.format_results`; UI `ResultCard.tsx`; `GET /api/results/{id}` |

#### RF-006 — Manejar errores de conexión y URLs inválidas
| | |
|--|--|
| **Descripción** | El sistema debe manejar errores de conexión y URLs inválidas. |
| **Prioridad** | Must |
| **Criterios de aceptación** | (1) URL inválida → error de validación sin romper el servicio. (2) Fallos de red / SerpAPI / scrape → estado `error` o degradación controlada con mensaje. (3) Logs con código/evento estructurado. |
| **Trazabilidad** | `image_validation.py`, `exceptions.py`, `logging_config.py`, `search_service.py`; UI mensajes de error |

---

### Requerimientos secundarios (Should Have)

#### RF-007 — Múltiples resultados ordenados cronológicamente
| | |
|--|--|
| **Descripción** | El sistema debería mostrar múltiples resultados ordenados cronológicamente. |
| **Prioridad** | Should |
| **Criterios de aceptación** | La UI y la API exponen una lista de candidatos (no solo uno), ordenada por el scoring (fecha + confiabilidad + autoridad de dominio). |
| **Trazabilidad** | `publication_scorer.py`; `components/search/` |

#### RF-008 — Reporte de confiabilidad del resultado
| | |
|--|--|
| **Descripción** | El sistema debería generar un reporte de confiabilidad del resultado. |
| **Prioridad** | Should |
| **Criterios de aceptación** | Cada ítem expone indicadores de confianza (`confirmed` / `provisional` / `pending`) y score cuando aplica. |
| **Trazabilidad** | `publication_scorer.py`; `ResultCard.tsx` |

#### RF-009 — Múltiples formatos de imagen
| | |
|--|--|
| **Descripción** | El sistema debería soportar imágenes en múltiples formatos (JPG, PNG, WebP, etc.). |
| **Prioridad** | Should |
| **Criterios de aceptación** | Validación por extensión y/o `Content-Type: image/*` para URL; subida acepta tipos de imagen habituales dentro del límite de tamaño configurado. |
| **Trazabilidad** | `image_validation.py`, `storage.py` |

---

### Requerimientos deseables (Could Have)

#### RF-010 — Cachear resultados para consultas repetidas
| | |
|--|--|
| **Descripción** | El sistema podría cachear resultados para consultas repetidas. |
| **Prioridad** | Could → **implementado** en la entrega actual (Must de facto para resiliencia ante reinicios, según devolución). |
| **Criterios de aceptación** | Con `DATABASE_URL`: caché de análisis por imagen, de payloads de motor y de scrape por URL (TTL configurable). Sin DB: operación en memoria (degradación documentada). |
| **Trazabilidad** | `db/cache.py`, `schema/001_init.sql`, `search_service.save_analysis_cache` |

#### RF-011 — Logs detallados de búsqueda
| | |
|--|--|
| **Descripción** | El sistema podría generar logs detallados de búsqueda. |
| **Prioridad** | Could → **implementado** (Must de facto para observabilidad). |
| **Criterios de aceptación** | Logs estructurados (texto en dev, JSON en prod) con `event`, `search_id` y fases (engine, static, deep, errores). |
| **Trazabilidad** | `logging_config.py`; eventos en `search_service`, scrapers y engines |

---

## 2. Requerimientos no funcionales

### RNF-001 — Performance
| | |
|--|--|
| **Descripción (1ª entrega)** | Tiempo de respuesta máximo de 30 segundos por consulta. |
| **Descripción actual** | Objetivo de diseño: completar una consulta típica en **≤ 30 s**. Con scraping dinámico y cold start de hosting free el tiempo puede superar ese techo; se mitiga con límite de candidatos, workers configurables y caché (RF-010). |
| **Prioridad** | Must (objetivo) |
| **Criterios de aceptación** | Tiempo medido y publicado en el informe del dataset; parámetros `SEARCH_MAX_CANDIDATE_URLS` y `SCRAPE_*_MAX_WORKERS` ajustables. |
| **Trazabilidad** | `search_service.py`, `scrape_config.py`, [dataset-prueba.md](dataset-prueba.md) |

### RNF-002 — Usabilidad
| | |
|--|--|
| **Descripción (1ª entrega)** | Interfaz CLI intuitiva con ayuda integrada (`--help`). |
| **Descripción actual** | Interfaz **web** intuitiva: ingreso de URL/archivo, progreso, resultados interpretables y mensajes de error. La operación local y el troubleshooting para evaluadores están en [manual-usuario.md](manual-usuario.md) y el [README](../README.md). |
| **Prioridad** | Must |
| **Criterios de aceptación** | Un usuario puede completar una búsqueda sin CLI; estados de carga y error visibles. |
| **Trazabilidad** | `identificador-web/` |

### RNF-003 — Confiabilidad
| | |
|--|--|
| **Descripción (1ª entrega)** | Tasa de éxito mínima del 80 % en el dataset de prueba. |
| **Descripción actual** | Tasa de éxito mínima del **70 %** en el dataset de prueba (umbral ajustado en la devolución de la 2ª entrega ante el cambio de motor de búsqueda). |
| **Prioridad** | Must |
| **Criterios de aceptación** | Dataset formal de ≥ 10 imágenes (`dataset/manifest.json`); caso correcto = dominio esperado en el top 10; precisión ≥ 70 %; informe en [dataset-prueba.md](dataset-prueba.md). |
| **Trazabilidad** | `scripts/run_dataset.py`, `identificador-api/dataset/` |

### RNF-004 — Mantenibilidad
| | |
|--|--|
| **Descripción** | Código documentado con docstrings y comentarios donde aportan claridad; módulos desacoplados (engines, scrapers, DB). |
| **Prioridad** | Should |
| **Criterios de aceptación** | Estructura de paquetes clara; documentación oficial en `docs/`; tipado en TypeScript y tipado/chequeos en el backend según tooling del repo. |
| **Trazabilidad** | Árbol `identificador-api/`, `identificador-web/`, `docs/` |

### RNF-005 — Portabilidad
| | |
|--|--|
| **Descripción (1ª entrega)** | Compatible con Python 3.8+. |
| **Descripción actual** | Backend fijado a **Python 3.11** (Render/Docker y tipado moderno). Frontend: Node.js compatible con la versión de Next.js del proyecto. |
| **Prioridad** | Must |
| **Criterios de aceptación** | Arranque documentado en README/manual; blueprint `render.yaml` / Dockerfile reproducibles. |
| **Trazabilidad** | `identificador-api/Dockerfile`, `.python-version` si aplica, README |

### RNF-006 — Seguridad
| | |
|--|--|
| **Descripción** | API keys almacenadas en variables de entorno (nunca en el repositorio). |
| **Prioridad** | Must |
| **Criterios de aceptación** | `SERPAPI_API_KEY`, credenciales Supabase y `DATABASE_URL` solo por env / secretos del host; plantilla `.env.example` sin secretos; `.env` en `.gitignore`. |
| **Trazabilidad** | `.env.example`, `.gitignore`, `render.yaml` (`sync: false` en secretos) |

---

## 3. Won't Have (alcance explícito)

| Ítem | Motivo |
|------|--------|
| Entrenar un modelo propio de embeddings visuales | Fuera de alcance PPS. |
| Autenticación de usuarios finales multi-tenant | Herramienta de demostración con rate limiting. |
| API TinEye nativa | Evaluada; se priorizó Bing/Yandex vía SerpAPI ([alternativas](alternativas-tecnologicas.md)). |
