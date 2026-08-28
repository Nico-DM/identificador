from urllib.parse import urlparse


def is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def normalize_url(url: str) -> str:
    from publication_scorer import normalize_url as _normalize_url

    return _normalize_url(url)
