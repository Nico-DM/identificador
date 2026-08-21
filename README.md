# Identificador de Artistas

**Proyecto universitario** — herramienta web para rastrear el origen y la difusión de imágenes en internet.

**Autor:** Nicolás Galetto

**Universidad:** Universidad Tecnológica Nacional

---

## ¿Qué hace?

Identificador permite a una persona introducir la **URL de una imagen pública** o **subir un archivo** y obtener pistas ordenadas sobre:

- **Dónde apareció** la imagen (páginas web enlazadas)
- **Fechas** inferidas a partir del contenido de esas páginas

El sistema combina **búsqueda inversa visual** ([Google Reverse Image](https://serpapi.com/google-reverse-image) vía [SerpApi](https://serpapi.com/)) con **scraping estático** de las URLs candidatas y un algoritmo de puntuación que prioriza los resultados más relevantes.

```
Usuario → Frontend (Next.js) → Backend (FastAPI) → SerpApi + Scrapers → Resultados ordenados
```

---

## Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Frontend | [Next.js](https://nextjs.org/) (App Router), TypeScript |
| Backend | [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11) |
| Búsqueda inversa | SerpApi — motor `google_reverse_image` |
| Scraping | BeautifulSoup (estático); Selenium opcional (búsqueda profunda) |
| Persistencia | Supabase / Postgres (opcional; sin configurar, el estado queda en memoria) |
| Almacenamiento | Supabase Storage (subida de archivos) |
| Despliegue | [Render](https://render.com/) (API) + [Vercel](https://vercel.com/) (web) |
| Keep-alive | [cron-job.org](https://cron-job.org/) — `GET /health` cada 10 min ([job](https://console.cron-job.org/jobs/7344787/history)) |

---

## Estructura del repositorio

```
identificador/
├── README.md                 # Este archivo
├── render.yaml               # Blueprint de despliegue en Render
├── scripts/dev.sh            # Levanta API + web en local (sin DB por defecto)
├── identificador-api/        # Backend FastAPI
│   ├── main.py               # App, CORS, routers
│   ├── routes/               # Endpoints HTTP
│   ├── search_service.py     # Orquestación de búsquedas
│   ├── serpapi_client.py     # SerpApi + extracción de URLs
│   ├── image_validation.py   # Validación de URLs de imagen
│   ├── env_util.py           # Helpers de variables de entorno
│   ├── identificador.py      # Scoring y ordenación de candidatas
│   ├── scraper_estatico.py
│   ├── scraper_dinamico.py
│   ├── db/                   # Persistencia Supabase/Postgres
│   └── scripts/
│       ├── smoke_test.py
│       └── apply_schema.py   # Aplica schema/001_init.sql
└── identificador-web/        # Frontend Next.js
    ├── app/page.tsx          # Página principal (layout)
    ├── components/search/    # UI de búsqueda
    ├── hooks/useSearch.ts    # Estado y polling
    └── app/api/              # Proxy hacia el backend
```

---

## Inicio rápido (desarrollo local)

### Requisitos

- Python 3.11
- Node.js (compatible con la versión de Next.js del proyecto)
- Clave de [SerpApi](https://serpapi.com/) (`SERPAPI_API_KEY`)

### Todo junto (recomendado)

```bash
./scripts/dev.sh
```

Levanta backend (`http://localhost:8000`) y frontend (`http://localhost:3000`) en una sola terminal. Por defecto usa memoria en lugar de Postgres; para usar Supabase/Postgres localmente: `DEV_USE_DATABASE=1 ./scripts/dev.sh`.

### Backend

```bash
cd identificador-api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # completar SERPAPI_API_KEY
python main.py
```

El servidor queda disponible en `http://localhost:8000`.

### Frontend

```bash
cd identificador-web
npm install
cp .env.example .env.local   # BACKEND_API_URL=http://localhost:8000
npm run dev
```

Abrí `http://localhost:3000`, pegá una URL de imagen o subí un archivo y esperá los resultados.

### Smoke test (solo backend)

```bash
cd identificador-api
source venv/bin/activate
python scripts/smoke_test.py --image-url "https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Color_of_Friendship.jpg/1920px-Color_of_Friendship.jpg"
```

---

## API (resumen)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/search` | Inicia búsqueda (`image_url` o archivo) → devuelve `search_id` |
| `GET` | `/api/results/{search_id}` | Estado (`processing` / `done` / `error`) y resultados |

El frontend expone las mismas rutas bajo `/api/` como proxy hacia el backend.

Flujo: el cliente envía la búsqueda → el backend responde con `search_id` y `status: processing` → el frontend hace polling cada ~2 s hasta recibir `done` o `error`.

---

## Variables de entorno

### Backend (`identificador-api/.env`)

| Variable | Descripción |
|----------|-------------|
| `SERPAPI_API_KEY` | Clave de SerpApi (obligatoria) |
| `SERPAPI_ENDPOINT` | Por defecto `https://serpapi.com/search.json` |
| `SERPAPI_ENGINE` | Por defecto `google_reverse_image` |
| `SEARCH_TTL_SECONDS` | TTL de búsquedas en memoria (por defecto `900`) |
| `ENVIRONMENT` | `development` en local; `production` en Render |
| `DATABASE_URL` | Opcional — Postgres/Supabase para persistencia y caché |
| `DISABLE_DATABASE` | `1`/`true` fuerza modo memoria (lo usa `scripts/dev.sh` por defecto) |
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `STORAGE_BUCKET` | Opcional — subida de archivos |

Plantilla completa: `identificador-api/.env.example`.

### Frontend (`identificador-web/.env.local`)

| Variable | Descripción |
|----------|-------------|
| `BACKEND_API_URL` | URL base del API (`http://localhost:8000` en local) |

---

## Despliegue

- **Backend:** [Render](https://render.com) con el blueprint [`render.yaml`](render.yaml) en la raíz (`rootDir: identificador-api`, health check `/health`).
- **Frontend:** [Vercel](https://vercel.com) apuntando a `identificador-web`, con `BACKEND_API_URL` configurada a la URL HTTPS pública de Render.

En Render, definí al menos `SERPAPI_API_KEY` como secreto. Tras desplegar el frontend, verificá con una URL de imagen pública.

En el plan free de Render el servicio se suspende tras inactividad. Para mantenerlo activo, un cron en [cron-job.org](https://cron-job.org/) hace `GET` cada **10 minutos** al endpoint `/health` del backend ([job configurado](https://console.cron-job.org/jobs/7344787/history)).

---

## Problemas frecuentes

**502 o "No se pudo conectar con el backend"** — Comprobá que FastAPI esté en marcha (`curl http://localhost:8000/health`) y que `BACKEND_API_URL` apunte solo al origen, sin path `/api/...`. Reiniciá `npm run dev` tras cambiar `.env.local`.

**En Vercel** — Misma variable `BACKEND_API_URL` con la URL HTTPS de Render; redeploy del frontend después de guardarla.

**URL de imagen rechazada** — Debe ser `http`/`https` y apuntar a una imagen (extensión permitida o `Content-Type: image/*`).

---

## Derechos del ícono

This favicon was generated using the following graphics from Twitter Twemoji:

- Graphics Title: 1f9d1-200d-1f3a8.svg
- Graphics Author: Copyright 2020 Twitter, Inc and other contributors (https://github.com/twitter/twemoji)
- Graphics Source: https://github.com/twitter/twemoji/blob/v14.0.2/assets/svg/1f9d1-200d-1f3a8.svg
- Graphics License: CC-BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
