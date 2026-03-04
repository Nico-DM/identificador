# Identificador API (MVP)

Backend FastAPI con polling: recibe `image_url`, consulta SerpApi Google Lens y procesa fechas con scrapers.

## Requisitos
- Python 3.10+
- Clave de SerpApi (250 usos/mes gratis)

## Variables de entorno
Crear `.env` con:
```
SERPAPI_API_KEY=tu_clave_serpapi
SERPAPI_ENDPOINT=https://serpapi.com/search.json
SERPAPI_ENGINE=google_lens
SEARCH_TTL_SECONDS=900
```

## Ejecutar en local
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Servidor levantado en `http://localhost:8000`.

## Endpoints
- `POST /api/search` (JSON con `image_url`) → devuelve `search_id`
- `GET /api/results/{search_id}` → consulta estado y resultados
- `GET /health` → verificar que API está activa

## Flujo de uso
1. Cliente envía: `POST /api/search { "image_url": "https://..." }`
2. Backend responde: `{ "search_id": "...", "status": "processing" }`
3. Cliente hace polling: `GET /api/results/{search_id}` cada 2s
4. Backend responde: `{ "status": "done", "results": [...] }` cuando termina

## Smoke test
Con el backend levantado:
```bash
python scripts/smoke_test.py --image-url https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Color_of_Friendship.jpg/1920px-Color_of_Friendship.jpg
```

Espera ~2 minutos (procesa hasta 120 URLs con scraper estático).

## Arquitectura MVP
- **Búsqueda:** SerpApi Google Lens (sin upload de imagen).
- **Procesamiento:** Scraper estático (BeautifulSoup) para extraer fechas.
- **Estado:** En memoria (se pierde al reiniciar servidor).
- **Scraper dinámico:** Desactivado en MVP (Selenium es lento).

## Próximos pasos
- [ ] Fase 2: Limitar a primeras 30 URLs de SerpApi.
- [ ] Fase 2: Agregar Supabase para persistencia.
- [ ] Despliegue: Railway (backend) + Vercel (frontend).


