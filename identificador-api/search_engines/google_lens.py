from search_engines.parsers import extract_google_match_metadata, extract_google_urls
from search_engines.serpapi import SerpApiSearchEngine


class GoogleLensEngine(SerpApiSearchEngine):
    """Google Lens via SerpAPI (`google_lens`)."""

    @property
    def engine_id(self) -> str:
        return "google_lens"

    def build_params(self, image_url: str, *, safe_search: bool) -> dict[str, str]:
        return {"url": image_url}

    def extract_urls(self, payload: dict) -> list[str]:
        return extract_google_urls(payload)

    def extract_match_metadata(self, payload: dict) -> dict[str, dict]:
        return extract_google_match_metadata(payload)
