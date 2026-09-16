# Requerimientos funcionales y no funcionales

## 1. Requerimientos funcionales

### RF-001 — Ingreso de imagen
| | |
|--|--|
| **Descripción** | El usuario puede iniciar un análisis a partir de una URL pública de imagen o de un archivo subido. |
| **Prioridad** | Must |
| **Criterios de aceptación** | (1) URL `http`/`https` con imagen válida es aceptada. (2) Archivo se acepta si Supabase Storage está configurado. (3) Entradas inválidas se rechazan con mensaje claro. |
| **Trazabilidad** | `identificador-api/routes/search.py`, `image_validation.py`, `storage.py`; `identificador-web/components/search/`, `hooks/useSearch.ts` |

### RF-002 — Búsqueda inversa de imagen
| | |
|--|--|
| **Descripción** | El sistema consulta un motor de búsqueda inversa configurable y obtiene URLs candidatas donde aparece la imagen. |
| **Prioridad** | Must |
| **Criterios de aceptación** | (1) Motor seleccionable por `SEARCH_ENGINE`. (2) La lógica de negocio no depende de un proveedor concreto (Strategy). (3) Fallos del proveedor se registran y se exponen como error de búsqueda. |
| **Trazabilidad** | `search_engines/base.py`, `factory.py`, `serpapi.py`, adaptadores; `search_service.py` |

### RF-003 — Obtención y recorte de candidatos
| | |
|--|--|
| **Descripción** | Se normalizan y limitan las URLs candidatas antes del scraping. |
| **Prioridad** | Must |
| **Criterios de aceptación** | Máximo de candidatos configurable (`SEARCH_MAX_CANDIDATE_URLS`, por defecto 30). |
| **Trazabilidad** | `search_service.py` |

### RF-004 — Extracción de fechas de publicación
| | |
|--|--|
| **Descripción** | Para cada candidato se intentan obtener fechas (metadatos, DOM, texto) asociadas a la publicación. |
| **Prioridad** | Must |
| **Criterios de aceptación** | Fase estática (BeautifulSoup) siempre; fase dinámica (Selenium) cuando corresponde (ver RF-008). |
| **Trazabilidad** | `static_scraper.py`, `dynamic_scraper.py`, `publication_scorer.py` |

### RF-005 — Ranking de publicación original
| | |
|--|--|
| **Descripción** | Los resultados se puntúan y ordenan priorizando fechas confiables y fuentes relevantes para identificar la aparición más temprana plausible. |
| **Prioridad** | Must |
| **Criterios de aceptación** | Cada resultado expone fecha (si hay), score/confianza, URL y metadatos de sitio; el orden es estable y reproducible para la misma entrada. |
| **Trazabilidad** | `publication_scorer.py`; UI `ResultCard.tsx` |

### RF-006 — Interfaz web de resultados
| | |
|--|--|
| **Descripción** | La interfaz muestra progreso, resultados parciales/finales e información suficiente para interpretar el origen. |
| **Prioridad** | Must |
| **Criterios de aceptación** | Polling hasta estado terminal; visualización de candidatos ordenados; feedback de error. |
| **Trazabilidad** | `identificador-web/app/page.tsx`, `hooks/useSearch.ts`, `components/search/` |

### RF-007 — Scraping estático
| | |
|--|--|
| **Descripción** | Extracción de fechas sin motor de navegador, en paralelo. |
| **Prioridad** | Must |
| **Criterios de aceptación** | Workers configurables; umbral de confianza (`SCRAPE_STATIC_CONFIDENCE_THRESHOLD`) decide si hace falta fase dinámica. |
| **Trazabilidad** | `static_scraper.py`, `scrape_config.py`, `publication_scorer.run_static_phase` |

### RF-008 — Scraping dinámico (Selenium)
| | |
|--|--|
| **Descripción** | Para plataformas que requieren JavaScript (Instagram, X/Twitter, ArtStation, DeviantArt, TikTok, Facebook) y para candidatos con baja confianza estática, el sistema ejecuta Selenium **por defecto** tras la fase estática, salvo que `SCRAPE_DYNAMIC_ENABLED=false`. |
| **Prioridad** | Must |
| **Criterios de aceptación** | (1) Habilitado por defecto en despliegue. (2) Autoarranque sin acción manual del usuario. (3) Endpoint manual `/api/search/{id}/deep` disponible como respaldo. (4) Timeouts y esperas documentados (ver [manual-usuario.md](manual-usuario.md#scraping-dinamico)). |
| **Trazabilidad** | `dynamic_scraper.py`, `scrape_config.py` (`JS_RENDER_PLATFORMS`), `search_service.process_search` / `process_deep_search` |

### RF-009 — Procesamiento asíncrono y consulta de estado
| | |
|--|--|
| **Descripción** | La búsqueda se ejecuta en segundo plano; el cliente consulta estado y progreso. |
| **Prioridad** | Must |
| **Criterios de aceptación** | `POST /api/search` → `search_id`; `GET /api/results/{id}` con `processing` / `deep_processing` / `done` / `error`. |
| **Trazabilidad** | `routes/search.py`, `search_service.py`; proxy Next.js `app/api/` |

### RF-010 — Caché y persistencia
| | |
|--|--|
| **Descripción** | Con `DATABASE_URL` configurada, el estado de búsquedas y cachés (análisis, motor, scrape por URL) persisten en Postgres/Supabase y sobreviven reinicios. |
| **Prioridad** | Must |
| **Criterios de aceptación** | Tablas del schema aplicadas; `/health` reporta persistencia activa; sin DB, el sistema opera en memoria (degradación documentada). |
| **Trazabilidad** | `db/cache.py`, `db/searches.py`, `schema/001_init.sql` |

### RF-011 — Motores alternativos y fallback
| | |
|--|--|
| **Descripción** | Además del motor principal, el sistema puede fusionar resultados de motores de respaldo cuando el primario aporta pocas URLs. |
| **Prioridad** | Should |
| **Criterios de aceptación** | `SEARCH_FALLBACK_ENGINES` acepta Bing y/o Yandex vía SerpAPI; fusión RRF; documentado en [alternativas-tecnologicas.md](alternativas-tecnologicas.md). |
| **Trazabilidad** | `search_engines/fused_engine.py`, `fusion.py`, `factory.py` |

---

## 2. Requerimientos no funcionales

### RNF-001 — Precisión de identificación
| | |
|--|--|
| **Descripción** | Sobre el dataset formal de 10 imágenes, la proporción de casos correctos (dominio esperado en el top 10) debe ser ≥ 70 %. |
| **Prioridad** | Must |
| **Criterios de aceptación** | Corrida reproducible con `scripts/run_dataset.py`; informe en [dataset-prueba.md](dataset-prueba.md). |
| **Trazabilidad** | `identificador-api/dataset/`, `scripts/run_dataset.py` |

### RNF-002 — Tiempo de respuesta
| | |
|--|--|
| **Descripción** | El flujo completo (búsqueda + scraping) debe completarse en un tiempo usable para demostración; el objetivo de diseño es mantener la fase de búsqueda inversa y el primer ranking en ventana razonable bajo carga normal. |
| **Prioridad** | Should |
| **Criterios de aceptación** | Tiempo promedio medido y publicado en el informe del dataset; workers y límites de URL ajustables por entorno. |
| **Trazabilidad** | `SEARCH_MAX_CANDIDATE_URLS`, `SCRAPE_*_MAX_WORKERS`, dataset |

### RNF-003 — Despliegue y disponibilidad
| | |
|--|--|
| **Descripción** | Frontend en Vercel; API en Render (Docker con Chrome para Selenium). |
| **Prioridad** | Must |
| **Criterios de aceptación** | Health check `/health`; blueprint `render.yaml`; keep-alive documentado en README. |
| **Trazabilidad** | `render.yaml`, `identificador-api/Dockerfile`, README |

### RNF-004 — Protección ante abuso
| | |
|--|--|
| **Descripción** | Rate limiting por IP en endpoints de búsqueda, deep y resultados. |
| **Prioridad** | Should |
| **Criterios de aceptación** | Activo en producción (`RATE_LIMIT_*` en `render.yaml`). |
| **Trazabilidad** | `rate_limit.py` |

### RNF-005 — Configurabilidad
| | |
|--|--|
| **Descripción** | Motores, umbrales, TTL y features se controlan por variables de entorno sin recompilar. |
| **Prioridad** | Must |
| **Criterios de aceptación** | Plantilla `.env.example`; documentado en manual y README. |
| **Trazabilidad** | `env_util.py`, `.env.example` |

### RNF-006 — Observabilidad
| | |
|--|--|
| **Descripción** | Logs estructurados de eventos de búsqueda, errores de API y fases de scrape. |
| **Prioridad** | Must |
| **Criterios de aceptación** | Formato JSON en producción; campos `event`, `search_id`, códigos de error. |
| **Trazabilidad** | `logging_config.py`, llamadas `logger.*` en `search_service` / engines |

---

## 3. Won't Have (alcance explícito)

| Ítem | Motivo |
|------|--------|
| Entrenar un modelo propio de embeddings visuales | Fuera de alcance PPS; se usan motores externos. |
| API pública multi-tenant con autenticación de usuarios finales | El producto es herramienta de demostración / uso abierto con rate limit. |
| Integración nativa TinEye (API propia) | Evaluada; se priorizó Bing/Yandex vía SerpAPI (ver alternativas). |
