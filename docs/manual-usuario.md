# Manual de usuario y operación (evaluadores)

Instructivo para instalar, configurar, usar e interpretar *Identificador de Artistas*. Pensado para la evaluación de la PPS; el resumen corto para uso general está en el [README](../README.md).

**Demostración pública (si está desplegada):** frontend [identificador-web.vercel.app](https://identificador-web.vercel.app/) · API en Render según `render.yaml`.

---

## 1. Qué hace el sistema

1. Recibe la **URL de una imagen** o un **archivo**.
2. Ejecuta **búsqueda inversa** (Google Reverse Image vía SerpAPI; opcionalmente Bing/Yandex).
3. **Scrapea** las páginas candidatas (estático; Selenium automático en sitios JS o baja confianza).
4. **Ordena** resultados por fechas y confiabilidad para orientar hacia la publicación más temprana plausible.

---

## 2. Instalación local

### Requisitos

- Python 3.11
- Node.js compatible con el Next.js del repo
- Cuenta [SerpAPI](https://serpapi.com/) (`SERPAPI_API_KEY`)
- (Opcional) proyecto Supabase para DB + Storage

### Arranque rápido

```bash
cp identificador-api/.env.example identificador-api/.env
# Editar SERPAPI_API_KEY
./scripts/dev.sh
```

- Web: http://localhost:3000  
- API: http://localhost:8000  
- Docs OpenAPI: http://localhost:8000/docs  

Con base de datos local: `DEV_USE_DATABASE=1 ./scripts/dev.sh`.

### Backend manual

```bash
cd identificador-api
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # completar claves
python main.py
```

### Frontend manual

```bash
cd identificador-web
npm install
cp .env.example .env.local   # BACKEND_API_URL=http://localhost:8000
npm run dev
```

---

## 3. Variables de entorno relevantes

| Variable | Rol |
|----------|-----|
| `SERPAPI_API_KEY` | Obligatoria |
| `SEARCH_ENGINE` | Default `google_reverse_image` |
| `SEARCH_FALLBACK_ENGINES` | Ej. `yandex_images,bing_reverse_image` |
| `DATABASE_URL` | Persistencia / caché (RF-010) |
| `DISABLE_DATABASE` | `1` fuerza memoria |
| `SUPABASE_*` / `STORAGE_BUCKET` | Subida de archivos |
| `SCRAPE_DYNAMIC_ENABLED` | Si `true` (default), Selenium corre automáticamente tras la fase estática |
| `SCRAPE_DYNAMIC_MAX_WORKERS` | Concurrencia Selenium (prod: 1) |
| `RATE_LIMIT_*` | Protección en producción |

Plantilla completa: `identificador-api/.env.example`.

---

## 4. Uso de la interfaz web

1. Abrir la web (local o Vercel).
2. Pegar una **URL pública de imagen** o elegir **archivo** (si Storage está configurado).
3. Iniciar la búsqueda y esperar la barra de progreso.
4. Revisar la lista ordenada: sitio, fecha inferida, enlace, confianza.

Estados típicos: `processing` → (opcional) `deep_processing` → `done`. Si falla el proveedor o la validación, se muestra `error` con mensaje.

El botón de “búsqueda profunda” solo aparece si quedó trabajo dinámico pendiente sin autoejecutarse (p. ej. configuración distinta o estados residuales); en el flujo normal **Selenium ya corre solo**.

---

## 5. Interpretación de resultados

| Campo | Significado |
|-------|-------------|
| Posición / orden | Prioridad del algoritmo (fechas más confiables y fuentes con más autoridad tienden a subir). |
| Fecha | Inferida del HTML/DOM de la página candidata; **no** es necesariamente la fecha de creación artística (puede ser indexación o edición de la página). |
| Confianza | `confirmed` / `provisional` / `pending` según score y fase. |
| URL | Página donde se encontró la imagen o una referencia. |

El sistema **sugiere** orígenes; la verificación humana del crédito al artista sigue siendo necesaria.

---

## 6. Scraping dinámico

### Cuándo corre

Con `SCRAPE_DYNAMIC_ENABLED=true` (default):

- Tras la fase estática, si hay URLs pendientes.
- Las plataformas **Instagram, X/Twitter, ArtStation, DeviantArt, TikTok, Facebook** se marcan siempre para Selenium.
- Otras URLs entran si la fecha estática falta o queda bajo el umbral de confianza (0.55).

### Esperas e implementación

- Chrome headless (imagen Docker en Render).
- Timeout de carga de página ~20 s.
- `WebDriverWait` ~8 s hasta `<body>`.
- Scrolls cortos para contenido lazy-load.

### Rate limiting

- API: `RATE_LIMIT_SEARCH_PER_HOUR`, `RATE_LIMIT_DEEP_PER_HOUR`, `RATE_LIMIT_RESULTS_PER_MINUTE`.
- Scraper: workers limitados (`SCRAPE_DYNAMIC_MAX_WORKERS`); no martillar el mismo host en ráfaga masiva.

### robots.txt y ética de scrape

El proyecto es académico y de bajo volumen. El scraper:

- No implementa un parser exhaustivo de `robots.txt` por dominio (limitación conocida).
- Se restringe a URLs ya públicas devueltas por motores de búsqueda.
- Usa timeouts agresivos y poco paralelismo en producción.
- **No** debe usarse para extracción masiva ni eludir controles de acceso.

Para producción comercial se debería añadir respeto explícito a `robots.txt` y políticas por sitio.

---

## 7. API (resumen)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Salud y modo de persistencia |
| `POST` | `/api/search` | Inicia búsqueda (JSON `image_url` o multipart) |
| `GET` | `/api/results/{search_id}` | Estado y resultados |
| `POST` | `/api/search/{search_id}/deep` | Deep manual (respaldo) |

---

## 8. Troubleshooting

| Síntoma | Qué revisar |
|---------|-------------|
| 502 / no conecta el frontend | `BACKEND_API_URL`, API arriba, cold start de Render |
| Rechazo de URL | Debe ser imagen `http(s)`; ver `image_validation.py` |
| Sin subida de archivo | Faltan `SUPABASE_*` / bucket |
| Pocos resultados útiles | Clave SerpAPI, motor, activar `SEARCH_FALLBACK_ENGINES` |
| Deep no corre | `SCRAPE_DYNAMIC_ENABLED`; en Render hace falta imagen Docker con Chrome |
| Resultados se pierden al reiniciar | Configurar `DATABASE_URL` y schema (`scripts/apply_schema.py`) |
| 429 | Rate limit; esperar la ventana o ajustar vars en no-prod |

Smoke test:

```bash
cd identificador-api && source venv/bin/activate
python scripts/smoke_test.py --image-url "<URL_IMAGEN>"
```

---

## 9. Documentación relacionada

- [requerimientos.md](requerimientos.md)
- [alternativas-tecnologicas.md](alternativas-tecnologicas.md)
- [contingencia-google-lens.md](contingencia-google-lens.md)
- [plan-de-pruebas.md](plan-de-pruebas.md)
- [dataset-prueba.md](dataset-prueba.md)
