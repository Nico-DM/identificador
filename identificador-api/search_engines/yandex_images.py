from search_engines.parsers import extract_yandex_match_metadata, extract_yandex_urls
from search_engines.serpapi import SerpApiSearchEngine


class YandexImagesEngine(SerpApiSearchEngine):
    """Yandex Images reverse search via SerpAPI (`yandex_images`)."""

    supports_safe_search = False

    @property
    def engine_id(self) -> str:
        return "yandex_images"

    def build_params(self, image_url: str, *, safe_search: bool) -> dict[str, str]:
        return {"url": image_url, "tab": "similar"}

    def extract_urls(self, payload: dict) -> list[str]:
        return extract_yandex_urls(payload)

    def extract_match_metadata(self, payload: dict) -> dict[str, dict]:
        return extract_yandex_match_metadata(payload)
