import os
import uuid

import requests
from exceptions import ServiceUnavailableError, ValidationError
from logging_config import get_logger

logger = get_logger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", "search-uploads")
UPLOAD_MAX_BYTES = int(os.getenv("UPLOAD_MAX_BYTES", "5242880"))

UPLOAD_IMAGE_EXTENSIONS = frozenset(
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

_EXT_CONTENT_TYPES: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".bmp": "image/bmp",
    ".ico": "image/x-icon",
    ".heic": "image/heic",
    ".heif": "image/heif",
}


def storage_enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def _auth_headers(content_type: str | None = None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _extension_from_filename(filename: str) -> str:
    base = os.path.basename(filename or "")
    _, ext = os.path.splitext(base)
    return ext.lower()


def _detect_image_format(content: bytes) -> str | None:
    if len(content) >= 3 and content[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if len(content) >= 8 and content[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if len(content) >= 6 and content[:6] in {b"GIF87a", b"GIF89a"}:
        return ".gif"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    if len(content) >= 12 and content[4:8] == b"ftyp":
        brand = content[8:12]
        if brand in {b"heic", b"heix", b"hevc", b"hevx", b"mif1"}:
            return ".heic"
        if brand in {b"heif", b"mif2"}:
            return ".heif"
        if brand == b"avif":
            return ".avif"
    if len(content) >= 2 and content[:2] == b"BM":
        return ".bmp"
    return None


def validate_upload(content: bytes, filename: str) -> tuple[str, str]:
    if not content:
        raise ValidationError("El archivo está vacío")
    if len(content) > UPLOAD_MAX_BYTES:
        raise ValidationError(
            f"El archivo supera el tamaño máximo ({UPLOAD_MAX_BYTES // (1024 * 1024)} MB)"
        )

    declared_ext = _extension_from_filename(filename)
    if declared_ext and declared_ext not in UPLOAD_IMAGE_EXTENSIONS:
        raise ValidationError("Tipo de archivo no permitido")

    detected_ext = _detect_image_format(content)
    if detected_ext is None:
        raise ValidationError("El archivo no es una imagen válida")

    if declared_ext and declared_ext != detected_ext:
        # JPEG puede declararse como .jpg o .jpeg
        jpeg_aliases = {".jpg", ".jpeg"}
        if not (declared_ext in jpeg_aliases and detected_ext in jpeg_aliases):
            raise ValidationError(
                "La extensión del archivo no coincide con su contenido"
            )

    ext = declared_ext if declared_ext in UPLOAD_IMAGE_EXTENSIONS else detected_ext
    content_type = _EXT_CONTENT_TYPES.get(ext, "application/octet-stream")
    return ext, content_type


def upload_search_image(content: bytes, filename: str) -> tuple[str, str]:
    if not storage_enabled():
        raise ServiceUnavailableError(
            "Supabase Storage no está configurado (SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY)",
            code="STORAGE_UNAVAILABLE",
        )

    ext, content_type = validate_upload(content, filename)
    object_path = f"uploads/{uuid.uuid4()}{ext}"
    url = f"{SUPABASE_URL}/storage/v1/object/{STORAGE_BUCKET}/{object_path}"

    response = requests.post(
        url,
        data=content,
        headers=_auth_headers(content_type),
        timeout=30,
    )
    if not response.ok:
        logger.error(
            "Supabase upload failed",
            extra={
                "event": "storage_upload_failed",
                "status": response.status_code,
                "body": response.text[:500],
            },
        )
        raise ServiceUnavailableError(
            "No se pudo subir la imagen a almacenamiento temporal",
            code="STORAGE_UPLOAD_FAILED",
        )

    public_url = (
        f"{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{object_path}"
    )
    return public_url, object_path


def delete_search_image(object_path: str) -> None:
    if not storage_enabled() or not object_path:
        return
    url = f"{SUPABASE_URL}/storage/v1/object/{STORAGE_BUCKET}/{object_path}"
    try:
        response = requests.delete(url, headers=_auth_headers(), timeout=15)
        if not response.ok:
            logger.warning(
                "Supabase delete failed",
                extra={
                    "event": "storage_delete_failed",
                    "object_path": object_path,
                    "status": response.status_code,
                },
            )
    except requests.RequestException as exc:
        logger.warning(
            "Supabase delete error",
            extra={"event": "storage_delete_error", "object_path": object_path},
            exc_info=exc,
        )
