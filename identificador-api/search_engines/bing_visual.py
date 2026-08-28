from search_engines.parsers import extract_bing_match_metadata, extract_bing_urls
from search_engines.serpapi import SerpApiSearchEngine


class BingVisualEngine(SerpApiSearchEngine):
    """Bing Visual Search via SerpAPI (`bing_reverse_image`)."""

    supports_safe_search = False

    @property
    def engine_id(self) -> str:
        return "bing_reverse_image"

    def build_params(self, image_url: str, *, safe_search: bool) -> dict[str, str]:
        return {"image_url": image_url}

    def extract_urls(self, payload: dict) -> list[str]:
        return extract_bing_urls(payload)

    def extract_match_metadata(self, payload: dict) -> dict[str, dict]:
        return extract_bing_match_metadata(payload)
