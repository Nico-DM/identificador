import logging
from urllib.parse import urlparse

import requests
from db.cache import get_lens_cache, set_lens_cache
from env_util import env_str
from publication_scorer import normalize_url

logger = logging.getLogger(__name__)

SERPAPI_API_KEY = env_str("SERPAPI_API_KEY")
SERPAPI_ENDPOINT = env_str("SERPAPI_ENDPOINT", "https://serpapi.com/search.json")
SERPAPI_ENGINE = env_str("SERPAPI_ENGINE", "google_reverse_image")


def is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def extract_match_metadata(payload: dict) -> dict[str, dict]:
    metadata: dict[str, dict] = {}

    def upsert(
        link: str,
        thumbnail: str | None,
        site_name: str | None,
        favicon: str | None = None,
    ) -> None:
        if not is_http_url(link):
            return
        key = normalize_url(link)
        entry = metadata.setdefault(key, {})
        if thumbnail and is_http_url(thumbnail):
            entry.setdefault("thumbnail", thumbnail)
        if site_name and site_name.strip():
            entry.setdefault("site_name", site_name.strip())
        if favicon and is_http_url(favicon):
            entry.setdefault("favicon", favicon)

    inline_thumbnails: dict[str, str] = {}
    for image in payload.get("inline_images", []) or []:
        page = image.get("link") or image.get("source")
        thumbnail = image.get("thumbnail")
        if (
            isinstance(page, str)
            and is_http_url(page)
            and isinstance(thumbnail, str)
            and is_http_url(thumbnail)
        ):
            inline_thumbnails[normalize_url(page)] = thumbnail

    for result in payload.get("image_results", []) or []:
        link = result.get("link")
        if not isinstance(link, str):
            continue
        thumbnail = result.get("thumbnail")
        thumb = (
            thumbnail
            if isinstance(thumbnail, str) and is_http_url(thumbnail)
            else inline_thumbnails.get(normalize_url(link))
        )
        source = result.get("source")
        name = source if isinstance(source, str) else None
        favicon = result.get("favicon")
        icon = favicon if isinstance(favicon, str) and is_http_url(favicon) else None
        upsert(link, thumb, name, icon)

    for match in payload.get("visual_matches", []) or []:
        link = match.get("link")
        if not isinstance(link, str):
            continue
        thumbnail = match.get("thumbnail")
        site_name = match.get("source")
        thumb = (
            thumbnail
            if isinstance(thumbnail, str) and is_http_url(thumbnail)
            else None
        )
        name = site_name if isinstance(site_name, str) else None
        source_icon = match.get("source_icon")
        icon = (
            source_icon
            if isinstance(source_icon, str) and is_http_url(source_icon)
            else None
        )
        upsert(link, thumb, name, icon)

    for image in payload.get("inline_images", []) or []:
        link = image.get("link") or image.get("source")
        if not isinstance(link, str):
            continue
        thumbnail = image.get("thumbnail")
        thumb = (
            thumbnail
            if isinstance(thumbnail, str) and is_http_url(thumbnail)
            else None
        )
        upsert(link, thumb, None)

    return metadata


def extract_urls_from_serpapi(payload: dict) -> list[str]:
    urls: list[str] = []

    for result in payload.get("image_results", []) or []:
        link = result.get("link")
        if isinstance(link, str) and is_http_url(link):
            urls.append(link)

    for match in payload.get("visual_matches", []) or []:
        for key in ("link", "source", "thumbnail"):
            value = match.get(key)
            if isinstance(value, str) and is_http_url(value):
                urls.append(value)

    for result in payload.get("related_content", []) or []:
        value = result.get("link")
        if isinstance(value, str) and is_http_url(value):
            urls.append(value)

    for image in payload.get("inline_images", []) or []:
        for key in ("link", "source", "thumbnail"):
            value = image.get(key)
            if isinstance(value, str) and is_http_url(value):
                urls.append(value)

    seen = set()
    unique_urls = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    return unique_urls


def serpapi_reverse_image_search(image_url: str, *, safe_search: bool = True) -> dict:
    if not SERPAPI_API_KEY:
        raise RuntimeError("SERPAPI_API_KEY no configurada")

    cached = get_lens_cache(image_url)
    if cached is not None:
        logger.info("SerpApi: response from Supabase cache")
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
        if "returned any results" in error_text or "hasn't returned any" in error_text:
            return {}
        raise RuntimeError(str(error_value))

    set_lens_cache(image_url, payload)
    return payload
