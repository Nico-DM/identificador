from dotenv import load_dotenv

load_dotenv()

import copy
import logging
import os
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from db.cache import (
    get_analysis_cache,
    get_lens_cache,
    set_analysis_cache,
    set_lens_cache,
)
from db.config import db_enabled
from db.repository import (
    prune_searches,
    search_create,
    search_get,
    search_persist,
    search_session,
)
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from identificador import (
    deserialize_pending_outcome,
    merge_publications,
    normalize_url,
    run_dynamic_phase,
    run_static_phase,
    serialize_pending_outcome,
)
from pydantic import BaseModel
from rate_limit import rate_limit_deep, rate_limit_results, rate_limit_search
from scrape_config import SCRAPE_DYNAMIC_ENABLED
from starlette.datastructures import UploadFile
from storage import delete_search_image, storage_enabled, upload_search_image

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")
SERPAPI_ENDPOINT = os.getenv("SERPAPI_ENDPOINT", "https://serpapi.com/search.json")
SERPAPI_ENGINE = os.getenv("SERPAPI_ENGINE", "google_reverse_image")
SEARCH_TTL_SECONDS = int(os.getenv("SEARCH_TTL_SECONDS", "900"))

IMAGE_EXTENSIONS = frozenset(
    {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".avif",
        ".bmp",
        ".ico",
        ".heic",
        ".heif",
    }
)

# (connect timeout, read timeout) para verificar Content-Type sin descargar el cuerpo completo
IMAGE_URL_VERIFY_TIMEOUT = (5, 10)
IMAGE_VERIFY_USER_AGENT = "Mozilla/5.0 (compatible; Identificador/1.0)"


class SearchRequest(BaseModel):
    image_url: str
    safe_search: bool = True


app = FastAPI()

# CORS: permitir desarrollo local y futuros despliegues en Vercel
ALLOWED_ORIGINS = [
    "http://localhost:3000",  # dev frontend
    "http://localhost:8000",  # dev backend
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    # Agregar dominio de Vercel en producción:
    "https://identificador-web-production.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS
    if os.getenv("ENVIRONMENT") == "development"
    else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _prune_searches() -> None:
    cutoff = _now_utc().timestamp() - SEARCH_TTL_SECONDS
    prune_searches(cutoff)


def _path_image_extension(parsed) -> str:
    path = parsed.path or ""
    segment = path.rstrip("/").split("/")[-1] if path else ""
    return os.path.splitext(segment)[1].lower()


def _response_content_type(resp: requests.Response) -> str | None:
    raw = resp.headers.get("Content-Type")
    if not raw:
        return None
    return raw.split(";")[0].strip().lower()


def _verify_url_returns_image(url: str) -> None:
    """Comprueba Content-Type image/* con HEAD; si no basta, GET en stream (solo cabeceras)."""
    try:
        head = requests.head(
            url,
            allow_redirects=True,
            timeout=IMAGE_URL_VERIFY_TIMEOUT,
            headers={"User-Agent": IMAGE_VERIFY_USER_AGENT},
        )
        try:
            if head.ok:
                ct = _response_content_type(head)
                if ct and ct.startswith("image/"):
                    return
        finally:
            head.close()
    except requests.RequestException:
        pass

    try:
        get = requests.get(
            url,
            stream=True,
            allow_redirects=True,
            timeout=IMAGE_URL_VERIFY_TIMEOUT,
            headers={"User-Agent": IMAGE_VERIFY_USER_AGENT},
        )
        try:
            ct = _response_content_type(get)
            if ct and ct.startswith("image/"):
                return
        finally:
            get.close()
    except requests.RequestException as exc:
        raise ValueError(
            "No se pudo verificar la URL como imagen (error de red, tiempo agotado o acceso denegado)"
        ) from exc

    raise ValueError(
        "La URL no es una imagen: el servidor no devolvio Content-Type image/*"
    )


def _validate_image_url(image_url: str) -> str:
    parsed = urlparse(image_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("image_url debe ser una URL http(s) valida")
    url = image_url.strip()
    parsed = urlparse(url)
    ext = _path_image_extension(parsed)
    if ext:
        if ext not in IMAGE_EXTENSIONS:
            raise ValueError(
                "La URL debe ser un enlace directo a imagen (extension no permitida)"
            )
        return url
    _verify_url_returns_image(url)
    return url


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def extract_match_metadata(payload: dict) -> dict[str, dict]:
    metadata: dict[str, dict] = {}

    def _upsert(
        link: str,
        thumbnail: str | None,
        site_name: str | None,
        favicon: str | None = None,
    ) -> None:
        if not _is_http_url(link):
            return
        key = normalize_url(link)
        entry = metadata.setdefault(key, {})
        if thumbnail and _is_http_url(thumbnail):
            entry.setdefault("thumbnail", thumbnail)
        if site_name and site_name.strip():
            entry.setdefault("site_name", site_name.strip())
        if favicon and _is_http_url(favicon):
            entry.setdefault("favicon", favicon)

    inline_thumbnails: dict[str, str] = {}
    for image in payload.get("inline_images", []) or []:
        page = image.get("link") or image.get("source")
        thumbnail = image.get("thumbnail")
        if (
            isinstance(page, str)
            and _is_http_url(page)
            and isinstance(thumbnail, str)
            and _is_http_url(thumbnail)
        ):
            inline_thumbnails[normalize_url(page)] = thumbnail

    for result in payload.get("image_results", []) or []:
        link = result.get("link")
        if not isinstance(link, str):
            continue
        thumbnail = result.get("thumbnail")
        thumb = (
            thumbnail
            if isinstance(thumbnail, str) and _is_http_url(thumbnail)
            else inline_thumbnails.get(normalize_url(link))
        )
        source = result.get("source")
        name = source if isinstance(source, str) else None
        favicon = result.get("favicon")
        icon = favicon if isinstance(favicon, str) and _is_http_url(favicon) else None
        _upsert(link, thumb, name, icon)

    for match in payload.get("visual_matches", []) or []:
        link = match.get("link")
        if not isinstance(link, str):
            continue
        thumbnail = match.get("thumbnail")
        site_name = match.get("source")
        thumb = (
            thumbnail
            if isinstance(thumbnail, str) and _is_http_url(thumbnail)
            else None
        )
        name = site_name if isinstance(site_name, str) else None
        source_icon = match.get("source_icon")
        icon = (
            source_icon
            if isinstance(source_icon, str) and _is_http_url(source_icon)
            else None
        )
        _upsert(link, thumb, name, icon)

    for image in payload.get("inline_images", []) or []:
        link = image.get("link") or image.get("source")
        if not isinstance(link, str):
            continue
        thumbnail = image.get("thumbnail")
        thumb = (
            thumbnail
            if isinstance(thumbnail, str) and _is_http_url(thumbnail)
            else None
        )
        _upsert(link, thumb, None)

    return metadata


def _site_name_fallback(url: str, platform: str | None) -> str:
    host = urlparse(url).netloc
    if host:
        return host.removeprefix("www.")
    return platform or "unknown"


def extract_urls_from_serpapi(payload: dict) -> list[str]:
    urls: list[str] = []

    for result in payload.get("image_results", []) or []:
        link = result.get("link")
        if isinstance(link, str) and _is_http_url(link):
            urls.append(link)

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
        for key in ("link", "source", "thumbnail"):
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


def _serpapi_reverse_image_search(image_url: str, *, safe_search: bool = True) -> dict:
    if not SERPAPI_API_KEY:
        raise RuntimeError("SERPAPI_API_KEY no configurada")

    cached = get_lens_cache(image_url)
    if cached is not None:
        logger.info("SerpApi: respuesta desde caché Supabase")
        return cached

    params: dict[str, str] = {
        "engine": SERPAPI_ENGINE,
        "api_key": SERPAPI_API_KEY,
        "safe": "active" if safe_search else "off",
    }
    if SERPAPI_ENGINE == "google_lens":
        params["url"] = image_url
    else:
        params["image_url"] = image_url

    response = requests.get(SERPAPI_ENDPOINT, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    error_value = payload.get("error")
    if error_value:
        error_text = str(error_value).lower()
        # SerpApi puede devolver este mensaje cuando no hay coincidencias; no es fallo tecnico.
        if "returned any results" in error_text or "hasn't returned any" in error_text:
            return {}
        raise RuntimeError(str(error_value))

    set_lens_cache(image_url, payload)
    return payload


def _analysis_snapshot(data: dict) -> dict:
    return {
        "status": data["status"],
        "phase": data.get("phase", "complete"),
        "results": data.get("results"),
        "raw_results": data.get("raw_results"),
        "error": data.get("error"),
        "processed_urls": data.get("processed_urls", 0),
        "total_urls": data.get("total_urls", 0),
        "static_total_urls": data.get("static_total_urls", 0),
        "match_metadata": data.get("match_metadata") or {},
        "pending_dynamic": data.get("pending_dynamic") or [],
        "deep_search_available": bool(data.get("deep_search_available", False)),
    }


def _save_analysis_cache(image_url: str, safe_search: bool, data: dict) -> None:
    if data.get("status") not in {"done", "static_done"}:
        return
    set_analysis_cache(image_url, _analysis_snapshot(data), safe_search=safe_search)
    logger.info(
        f"Análisis cacheado para imagen (safe_search={'active' if safe_search else 'off'})"
    )


def _set_search(
    search_id: str,
    status: str,
    *,
    results=None,
    error: str | None = None,
    phase: str | None = None,
) -> None:
    with search_session(search_id) as current:
        if not current:
            return
        current["status"] = status
        if results is not None:
            current["results"] = results
        current["error"] = error
        if phase is not None:
            current["phase"] = phase
        current["updated_at"] = _now_utc()
    search_persist(search_id, force=True)


def _update_search_progress(
    search_id: str,
    *,
    results: list | None = None,
    processed: int | None = None,
    total: int | None = None,
) -> None:
    with search_session(search_id) as current:
        if not current:
            return
        if current["status"] not in {"processing", "deep_processing"}:
            return
        if results is not None:
            current["results"] = results
        if processed is not None:
            current["processed_urls"] = processed
        if total is not None:
            current["total_urls"] = total
        current["updated_at"] = _now_utc()
    search_persist(search_id)


def _format_result_item(item: dict, match_metadata: dict) -> dict:
    created = item.get("created_utc")
    url = item.get("link")
    platform = item.get("platform")
    meta = match_metadata.get(normalize_url(url), {}) if url else {}
    return {
        "date": created.isoformat() if isinstance(created, datetime) else None,
        "platform": platform,
        "url": url,
        "score": item.get("score"),
        "source": item.get("source"),
        "confidence": item.get(
            "confidence", "pending" if created is None else "confirmed"
        ),
        "thumbnail": meta.get("thumbnail"),
        "favicon": meta.get("favicon"),
        "site_name": meta.get("site_name")
        or (_site_name_fallback(url, platform) if url else (platform or "unknown")),
    }


def _format_results(raw_results: list, match_metadata: dict) -> list:
    return [_format_result_item(item, match_metadata) for item in raw_results]


def _build_results_response(search_id: str, data: dict) -> dict:
    deep_available = data.get("deep_search_available", False)
    pending_count = len(data.get("pending_dynamic") or [])
    return {
        "search_id": search_id,
        "status": data["status"],
        "phase": data.get("phase", "complete"),
        "results": data["results"],
        "error": data["error"],
        "progress": {
            "processed": data.get("processed_urls", 0),
            "total": data.get("total_urls", 0),
        },
        "deep_search": {
            "available": deep_available,
            "pending_urls": pending_count if deep_available else 0,
        },
    }


def _process_search(
    search_id: str,
    image_url: str,
    *,
    safe_search: bool = True,
    upload_object_path: str | None = None,
) -> None:
    try:
        logger.info(
            f"Iniciando búsqueda {search_id} para imagen: {image_url} "
            f"(safe_search={'active' if safe_search else 'off'})"
        )
        payload = _serpapi_reverse_image_search(image_url, safe_search=safe_search)
        urls = extract_urls_from_serpapi(payload)
        match_metadata = extract_match_metadata(payload)
        logger.info(f"SerpApi devolvió {len(urls)} URLs para búsqueda {search_id}")

        search_inputs = [{"link": url, "source": "serpapi"} for url in urls]
        total_urls = len(search_inputs)
        _update_search_progress(search_id, results=[], processed=0, total=total_urls)

        def _on_static_progress(processed: int, total: int, partial: list) -> None:
            formatted_partial = _format_results(partial, match_metadata)
            _update_search_progress(
                search_id,
                results=formatted_partial,
                processed=processed,
                total=total,
            )

        static_results, pending_outcomes = run_static_phase(
            search_inputs,
            on_progress=_on_static_progress,
        )

        formatted = _format_results(static_results, match_metadata)
        pending_serialized = [
            serialize_pending_outcome(item) for item in pending_outcomes
        ]
        deep_available = SCRAPE_DYNAMIC_ENABLED and len(pending_outcomes) > 0

        with search_session(search_id) as current:
            if not current:
                return
            current["match_metadata"] = match_metadata
            current["pending_dynamic"] = pending_serialized
            current["deep_search_available"] = deep_available
            current["static_total_urls"] = total_urls
            current["raw_results"] = static_results
            current["results"] = formatted
            current["updated_at"] = _now_utc()
        search_persist(search_id, force=True)

        logger.info(
            f"Fase estatica completada: {len(static_results)} resultados, "
            f"{len(pending_outcomes)} pendientes de busqueda profunda"
        )

        if deep_available:
            _set_search(search_id, "static_done", phase="static")
        else:
            _set_search(search_id, "done", phase="complete")
        current = search_get(search_id)
        if current:
            _save_analysis_cache(image_url, safe_search, current)
        logger.info(f"Búsqueda {search_id} fase estatica completada")
    except Exception as exc:
        logger.exception("Error procesando búsqueda %s", search_id)
        _set_search(search_id, "error", results=None, error=str(exc), phase="complete")
    finally:
        if upload_object_path:
            delete_search_image(upload_object_path)


def _process_deep_search(search_id: str) -> None:
    try:
        current = search_get(search_id)
        if not current:
            return
        pending_data = list(current.get("pending_dynamic") or [])
        match_metadata = dict(current.get("match_metadata") or {})
        existing_raw = list(current.get("raw_results") or [])
        static_total = current.get("static_total_urls", 0)

        pending_outcomes = [deserialize_pending_outcome(item) for item in pending_data]
        deep_total = len(pending_outcomes)
        _update_search_progress(
            search_id,
            processed=static_total,
            total=static_total + deep_total,
        )

        def _on_deep_progress(
            processed: int, total: int, partial_updates: list
        ) -> None:
            merged_raw = merge_publications(existing_raw, partial_updates)
            formatted = _format_results(merged_raw, match_metadata)
            _update_search_progress(
                search_id,
                results=formatted,
                processed=processed,
                total=total,
            )

        updates = run_dynamic_phase(
            pending_outcomes,
            on_progress=_on_deep_progress,
            static_processed=static_total,
            static_total=static_total,
        )

        merged_raw = merge_publications(existing_raw, updates)
        formatted = _format_results(merged_raw, match_metadata)

        with search_session(search_id) as current:
            if not current:
                return
            current["raw_results"] = merged_raw
            current["results"] = formatted
            current["deep_search_available"] = False
            current["pending_dynamic"] = []
            current["processed_urls"] = static_total + deep_total
            current["total_urls"] = static_total + deep_total
            current["updated_at"] = _now_utc()
        search_persist(search_id, force=True)

        _set_search(search_id, "done", results=formatted, error=None, phase="complete")
        current = search_get(search_id)
        if current:
            _save_analysis_cache(
                current["image_url"],
                current.get("safe_search", True),
                current,
            )
        logger.info(
            f"Búsqueda profunda {search_id} completada: {len(formatted)} resultados"
        )
    except Exception as exc:
        logger.exception("Error en búsqueda profunda %s", search_id)
        with search_session(search_id) as current:
            if current:
                current["deep_search_available"] = False
                current["updated_at"] = _now_utc()
        _set_search(
            search_id,
            "error",
            error=str(exc),
            phase="complete",
        )


@app.get("/")
async def root():
    return {"status": "ok"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "persistence": "supabase" if db_enabled() else "memory",
        "file_upload": storage_enabled(),
    }


def _parse_safe_search(value) -> bool:
    if value is None:
        return True
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    return normalized not in {"0", "false", "no", "off"}


def _start_search(
    background_tasks: BackgroundTasks,
    image_url: str,
    safe_search: bool,
    *,
    upload_object_path: str | None = None,
) -> dict:
    search_id = str(uuid.uuid4())
    now = _now_utc()

    cached = get_analysis_cache(image_url, safe_search=safe_search)
    if cached is not None:
        if upload_object_path:
            delete_search_image(upload_object_path)
        data = copy.deepcopy(cached)
        data["image_url"] = image_url
        data["safe_search"] = safe_search
        data["created_at"] = now
        data["updated_at"] = now
        search_create(search_id, data)
        logger.info(
            f"Búsqueda {search_id} restaurada desde caché "
            f"(status={data['status']}, resultados={len(data.get('results') or [])})"
        )
        return {"search_id": search_id, "status": data["status"], "cached": True}

    logger.info(f"Nueva búsqueda iniciada - ID: {search_id}, URL: {image_url}")
    search_create(
        search_id,
        {
            "status": "processing",
            "phase": "static",
            "results": None,
            "raw_results": None,
            "error": None,
            "processed_urls": 0,
            "total_urls": 0,
            "static_total_urls": 0,
            "image_url": image_url,
            "safe_search": safe_search,
            "upload_object_path": upload_object_path,
            "match_metadata": {},
            "pending_dynamic": [],
            "deep_search_available": False,
            "created_at": now,
            "updated_at": now,
        },
    )

    background_tasks.add_task(
        _process_search,
        search_id,
        image_url,
        safe_search=safe_search,
        upload_object_path=upload_object_path,
    )

    return {"search_id": search_id, "status": "processing"}


@app.post("/api/search")
async def search(
    request: Request,
    background_tasks: BackgroundTasks,
    _: None = Depends(rate_limit_search),
):
    _prune_searches()

    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        if not storage_enabled():
            raise HTTPException(
                status_code=503,
                detail="Subida por archivo no disponible: configurá Supabase Storage",
            )
        form = await request.form()
        upload = form.get("file")
        safe_search = _parse_safe_search(form.get("safe_search"))

        if not isinstance(upload, UploadFile):
            raise HTTPException(status_code=400, detail="Falta el archivo de imagen")

        filename = getattr(upload, "filename", None) or "upload.jpg"
        content = await upload.read()

        try:
            image_url, object_path = upload_search_image(content, filename)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        return _start_search(
            background_tasks,
            image_url,
            safe_search,
            upload_object_path=object_path,
        )

    try:
        body = await request.json()
        payload = SearchRequest(**body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="JSON invalido") from exc

    try:
        image_url = _validate_image_url(payload.image_url)
    except ValueError as exc:
        logger.warning(f"URL de imagen inválida: {payload.image_url}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _start_search(background_tasks, image_url, payload.safe_search)


@app.post("/api/search/{search_id}/deep")
async def deep_search(
    search_id: str,
    background_tasks: BackgroundTasks,
    _: None = Depends(rate_limit_deep),
):
    _prune_searches()

    data = search_get(search_id)

    if not data:
        raise HTTPException(status_code=404, detail="Busqueda no encontrada")

    if data["status"] == "deep_processing":
        raise HTTPException(status_code=409, detail="Busqueda profunda ya en curso")

    if data["status"] != "static_done":
        raise HTTPException(
            status_code=400,
            detail="La busqueda profunda solo esta disponible tras completar la fase estatica",
        )

    if not data.get("deep_search_available"):
        raise HTTPException(status_code=400, detail="Busqueda profunda no disponible")

    with search_session(search_id) as current:
        if not current or current["status"] != "static_done":
            raise HTTPException(status_code=409, detail="Estado de busqueda invalido")
        current["status"] = "deep_processing"
        current["phase"] = "deep"
        deep_total = len(current.get("pending_dynamic") or [])
        static_total = current.get("static_total_urls", 0)
        current["processed_urls"] = static_total
        current["total_urls"] = static_total + deep_total
        current["updated_at"] = _now_utc()
    search_persist(search_id, force=True)

    background_tasks.add_task(_process_deep_search, search_id)

    return {"search_id": search_id, "status": "deep_processing"}


@app.get("/api/results/{search_id}")
async def get_results(search_id: str, _: None = Depends(rate_limit_results)):
    _prune_searches()

    data = search_get(search_id)

    if not data:
        raise HTTPException(status_code=404, detail="Busqueda no encontrada")

    return _build_results_response(search_id, data)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
