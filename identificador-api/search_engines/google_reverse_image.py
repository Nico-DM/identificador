from search_engines.parsers import extract_google_match_metadata, extract_google_urls
from search_engines.serpapi import SerpApiSearchEngine


class GoogleReverseImageEngine(SerpApiSearchEngine):
    """Google Reverse Image via SerpAPI (`google_reverse_image`)."""

    @property
    def engine_id(self) -> str:
        return "google_reverse_image"

    def build_params(self, image_url: str, *, safe_search: bool) -> dict[str, str]:
        return {"image_url": image_url}

    def extract_urls(self, payload: dict) -> list[str]:
        return extract_google_urls(payload)

    def extract_match_metadata(self, payload: dict) -> dict[str, dict]:
        return extract_google_match_metadata(payload)
