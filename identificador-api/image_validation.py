import os
from urllib.parse import urlparse

import requests

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

IMAGE_URL_VERIFY_TIMEOUT = (5, 10)
IMAGE_VERIFY_USER_AGENT = "Mozilla/5.0 (compatible; Identificador/1.0)"


def path_image_extension(parsed) -> str:
    path = parsed.path or ""
    segment = path.rstrip("/").split("/")[-1] if path else ""
    return os.path.splitext(segment)[1].lower()


def _response_content_type(resp: requests.Response) -> str | None:
    raw = resp.headers.get("Content-Type")
    if not raw:
        return None
    return raw.split(";")[0].strip().lower()


def verify_url_returns_image(url: str) -> None:
    """Verify Content-Type image/* via HEAD; fall back to streaming GET (headers only)."""
    try:
        head = requests.head(
            url,
            allow_redirects=True,
            timeout=IMAGE_URL_VERIFY_TIMEOUT,
            headers={"User-Agent": IMAGE_VERIFY_USER_AGENT},
        )
        try:
            if head.ok:
                content_type = _response_content_type(head)
                if content_type and content_type.startswith("image/"):
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
            content_type = _response_content_type(get)
            if content_type and content_type.startswith("image/"):
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


def validate_image_url(image_url: str) -> str:
    parsed = urlparse(image_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("image_url debe ser una URL http(s) valida")
    url = image_url.strip()
    parsed = urlparse(url)
    ext = path_image_extension(parsed)
    if ext:
        if ext not in IMAGE_EXTENSIONS:
            raise ValueError(
                "La URL debe ser un enlace directo a imagen (extension no permitida)"
            )
        return url
    verify_url_returns_image(url)
    return url
