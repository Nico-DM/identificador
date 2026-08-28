from env_util import parse_safe_search
from exceptions import (
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from image_validation import validate_image_url
from logging_config import get_logger
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError
from rate_limit import rate_limit_deep, rate_limit_results, rate_limit_search
from search_service import (
    build_results_response,
    now_utc,
    process_deep_search,
    prune_expired_searches,
    search_get,
    search_persist,
    search_session,
    start_search,
)
from starlette.datastructures import UploadFile
from storage import storage_enabled, upload_search_image

logger = get_logger(__name__)

router = APIRouter()


class SearchRequest(BaseModel):
    image_url: str
    safe_search: bool = True


@router.post("/api/search")
async def search(
    request: Request,
    background_tasks: BackgroundTasks,
    _: None = Depends(rate_limit_search),
):
    prune_expired_searches()

    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        if not storage_enabled():
            raise ServiceUnavailableError(
                "Subida por archivo no disponible: configurá Supabase Storage",
                code="STORAGE_UNAVAILABLE",
            )
        form = await request.form()
        upload = form.get("file")
        safe_search = parse_safe_search(form.get("safe_search"))

        if not isinstance(upload, UploadFile):
            raise ValidationError("Falta el archivo de imagen")

        filename = getattr(upload, "filename", None) or "upload.jpg"
        content = await upload.read()
        image_url, object_path = upload_search_image(content, filename)

        return start_search(
            background_tasks,
            image_url,
            safe_search,
            upload_object_path=object_path,
        )

    try:
        body = await request.json()
        payload = SearchRequest(**body)
    except PydanticValidationError as exc:
        raise ValidationError("JSON invalido") from exc

    try:
        image_url = validate_image_url(payload.image_url)
    except ValidationError:
        logger.warning(
            "Invalid image URL rejected",
            extra={"event": "invalid_image_url", "image_url": payload.image_url},
        )
        raise

    return start_search(background_tasks, image_url, payload.safe_search)


@router.post("/api/search/{search_id}/deep")
async def deep_search(
    search_id: str,
    background_tasks: BackgroundTasks,
    _: None = Depends(rate_limit_deep),
):
    prune_expired_searches()

    data = search_get(search_id)

    if not data:
        raise NotFoundError("Busqueda no encontrada")

    if data["status"] == "deep_processing":
        raise ConflictError("Busqueda profunda ya en curso")

    if data["status"] != "static_done":
        raise ValidationError(
            "La busqueda profunda solo esta disponible tras completar la fase estatica"
        )

    if not data.get("deep_search_available"):
        raise ValidationError("Busqueda profunda no disponible")

    with search_session(search_id) as current:
        if not current or current["status"] != "static_done":
            raise ConflictError("Estado de busqueda invalido")
        current["status"] = "deep_processing"
        current["phase"] = "deep"
        deep_total = len(current.get("pending_dynamic") or [])
        static_total = current.get("static_total_urls", 0)
        current["processed_urls"] = static_total
        current["total_urls"] = static_total + deep_total
        current["updated_at"] = now_utc()
    search_persist(search_id, force=True)

    background_tasks.add_task(process_deep_search, search_id)

    return {"search_id": search_id, "status": "deep_processing"}


@router.get("/api/results/{search_id}")
async def get_results(search_id: str, _: None = Depends(rate_limit_results)):
    prune_expired_searches()

    data = search_get(search_id)

    if not data:
        raise NotFoundError("Busqueda no encontrada")

    return build_results_response(search_id, data)
