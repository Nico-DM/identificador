from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import datetime, timezone
from urllib.parse import urlparse
import os
import threading
import uuid
import requests

from identificador import get_sorted_dates

load_dotenv()

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")
SERPAPI_ENDPOINT = os.getenv("SERPAPI_ENDPOINT", "https://serpapi.com/search.json")
SERPAPI_ENGINE = os.getenv("SERPAPI_ENGINE", "google_lens")
SEARCH_TTL_SECONDS = int(os.getenv("SEARCH_TTL_SECONDS", "900"))


class SearchRequest(BaseModel):
    image_url: str


app = FastAPI()

# CORS: permitir desarrollo local y futuros despliegues en Vercel
ALLOWED_ORIGINS = [
    "http://localhost:3000",  # dev frontend
    "http://localhost:8000",  # dev backend
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    # Agregar dominio de Vercel en producción:
    # "https://identificador-web-production.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if os.getenv("ENVIRONMENT") == "development" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_searches_lock = threading.Lock()
_searches_db = {}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _prune_searches() -> None:
    cutoff = _now_utc().timestamp() - SEARCH_TTL_SECONDS
    with _searches_lock:
        stale = [key for key, value in _searches_db.items() if value["created_at"].timestamp() < cutoff]
        for key in stale:
            _searches_db.pop(key, None)


def _validate_image_url(image_url: str) -> str:
    parsed = urlparse(image_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("image_url debe ser una URL http(s) valida")
    return image_url.strip()


def _is_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except Exception:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def extract_urls_from_serpapi(payload: dict) -> list[str]:
    urls: list[str] = []

    for match in payload.get("visual_matches", []) or []:
        for key in ("link", "source", "thumbnail"):
            value = match.get(key)
            if isinstance(value, str) and _is_http_url(value):
                urls.append(value)

    for result in payload.get("related_content", []) or []:
        value = result.get("link")
        if isinstance(value, str) and _is_http_url(value):
            urls.append(value)

    for image in payload.get("inline_images", []) or []:
        for key in ("link", "thumbnail"):
            value = image.get(key)
            if isinstance(value, str) and _is_http_url(value):
                urls.append(value)

    seen = set()
    unique_urls = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    return unique_urls


def _serpapi_lens_search(image_url: str) -> list[str]:
    if not SERPAPI_API_KEY:
        raise RuntimeError("SERPAPI_API_KEY no configurada")

    params = {
        "engine": SERPAPI_ENGINE,
        "url": image_url,
        "api_key": SERPAPI_API_KEY,
    }
    response = requests.get(SERPAPI_ENDPOINT, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    error_value = payload.get("error")
    if error_value:
        error_text = str(error_value).lower()
        # Google Lens puede devolver este mensaje cuando no hay coincidencias; no es fallo tecnico.
        if "returned any results" in error_text:
            return []
        raise RuntimeError(str(error_value))

    return extract_urls_from_serpapi(payload)


def _set_search(search_id: str, status: str, results=None, error: str | None = None) -> None:
    with _searches_lock:
        current = _searches_db.get(search_id)
        if not current:
            return
        current["status"] = status
        current["results"] = results
        current["error"] = error
        current["updated_at"] = _now_utc()


def _process_search(search_id: str, image_url: str) -> None:
    try:
        urls = _serpapi_lens_search(image_url)
        search_inputs = [{"link": url, "source": "serpapi"} for url in urls]
        sorted_results = get_sorted_dates(search_inputs)

        formatted = []
        for item in sorted_results:
            created = item.get("created_utc")
            formatted.append(
                {
                    "date": created.isoformat() if isinstance(created, datetime) else None,
                    "platform": item.get("platform"),
                    "url": item.get("link"),
                    "score": item.get("score"),
                    "source": item.get("source"),
                }
            )

        _set_search(search_id, "done", results=formatted, error=None)
    except Exception as exc:
        _set_search(search_id, "error", results=None, error=str(exc))


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/search")
async def search(background_tasks: BackgroundTasks, payload: SearchRequest):
    _prune_searches()

    try:
        image_url = _validate_image_url(payload.image_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    search_id = str(uuid.uuid4())
    now = _now_utc()
    with _searches_lock:
        _searches_db[search_id] = {
            "status": "processing",
            "results": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }

    background_tasks.add_task(_process_search, search_id, image_url)

    return {"search_id": search_id, "status": "processing"}


@app.get("/api/results/{search_id}")
async def get_results(search_id: str):
    _prune_searches()

    with _searches_lock:
        data = _searches_db.get(search_id)

    if not data:
        raise HTTPException(status_code=404, detail="Busqueda no encontrada")

    return {
        "search_id": search_id,
        "status": data["status"],
        "results": data["results"],
        "error": data["error"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)