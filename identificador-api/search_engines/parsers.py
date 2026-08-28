from search_engines.utils import is_http_url, normalize_url


def extract_google_match_metadata(payload: dict) -> dict[str, dict]:
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


def extract_google_urls(payload: dict) -> list[str]:
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

    return _dedupe_urls(urls)


def extract_bing_match_metadata(payload: dict) -> dict[str, dict]:
    metadata: dict[str, dict] = {}

    for item in payload.get("related_content", []) or []:
        link = item.get("link")
        if not isinstance(link, str) or not is_http_url(link):
            continue
        key = normalize_url(link)
        entry = metadata.setdefault(key, {})
        thumbnail = item.get("thumbnail") or item.get("original")
        if isinstance(thumbnail, str) and is_http_url(thumbnail):
            entry.setdefault("thumbnail", thumbnail)
        title = item.get("title")
        if isinstance(title, str) and title.strip():
            entry.setdefault("site_name", title.strip())

    return metadata


def extract_bing_urls(payload: dict) -> list[str]:
    urls: list[str] = []

    for item in payload.get("related_content", []) or []:
        link = item.get("link")
        if isinstance(link, str) and is_http_url(link):
            urls.append(link)
        for key in ("original", "thumbnail"):
            value = item.get(key)
            if isinstance(value, str) and is_http_url(value):
                urls.append(value)

    return _dedupe_urls(urls)


def extract_yandex_match_metadata(payload: dict) -> dict[str, dict]:
    metadata: dict[str, dict] = {}

    def upsert(item: dict) -> None:
        link = item.get("link")
        if not isinstance(link, str) or not is_http_url(link):
            return
        key = normalize_url(link)
        entry = metadata.setdefault(key, {})
        for thumb_key in ("thumbnail", "original_image", "original"):
            thumbnail = item.get(thumb_key)
            if isinstance(thumbnail, str) and is_http_url(thumbnail):
                entry.setdefault("thumbnail", thumbnail)
                break
        source = item.get("source") or item.get("title")
        if isinstance(source, str) and source.strip():
            entry.setdefault("site_name", source.strip())

    for item in payload.get("image_results", []) or []:
        upsert(item)

    for item in payload.get("similar_images", []) or []:
        upsert(item)

    return metadata


def extract_yandex_urls(payload: dict) -> list[str]:
    urls: list[str] = []

    for section in ("image_results", "similar_images"):
        for item in payload.get(section, []) or []:
            link = item.get("link")
            if isinstance(link, str) and is_http_url(link):
                urls.append(link)
            for key in ("original_image", "original", "thumbnail"):
                value = item.get(key)
                if isinstance(value, str) and is_http_url(value):
                    urls.append(value)

    return _dedupe_urls(urls)


def _dedupe_urls(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_urls: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    return unique_urls
