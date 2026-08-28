import logging
from abc import abstractmethod

import requests
from db.cache import get_engine_cache, set_engine_cache
from env_util import env_str

from search_engines.base import SearchEngine, SearchOutcome

logger = logging.getLogger(__name__)

SERPAPI_API_KEY = env_str("SERPAPI_API_KEY")
SERPAPI_ENDPOINT = env_str("SERPAPI_ENDPOINT", "https://serpapi.com/search.json")


class SerpApiSearchEngine(SearchEngine):
    """Base class for SerpAPI-backed reverse-image search strategies."""

    supports_safe_search: bool = True

    @property
    @abstractmethod
    def engine_id(self) -> str:
        """Provider-specific engine identifier (SerpAPI `engine` param)."""

    @abstractmethod
    def build_params(self, image_url: str, *, safe_search: bool) -> dict[str, str]:
        """Build engine-specific SerpAPI query parameters."""

    @abstractmethod
    def extract_urls(self, payload: dict) -> list[str]:
        """Extract candidate URLs from a SerpAPI response payload."""

    @abstractmethod
    def extract_match_metadata(self, payload: dict) -> dict[str, dict]:
        """Extract thumbnail/site metadata keyed by normalized URL."""

    @property
    def name(self) -> str:
        return self.engine_id

    def search(self, image_url: str, *, safe_search: bool = True) -> SearchOutcome:
        if not SERPAPI_API_KEY:
            raise RuntimeError("SERPAPI_API_KEY no configurada")

        cached = get_engine_cache(image_url, engine=self.engine_id)
        if cached is not None:
            logger.info("%s: response from engine cache", self.engine_id)
            payload = cached
        else:
            payload = self._fetch(image_url, safe_search=safe_search)
            set_engine_cache(image_url, payload, engine=self.engine_id)

        return SearchOutcome(
            urls=self.extract_urls(payload),
            match_metadata=self.extract_match_metadata(payload),
            raw_payload=payload,
        )

    def _fetch(self, image_url: str, *, safe_search: bool) -> dict:
        params = {
            "engine": self.engine_id,
            "api_key": SERPAPI_API_KEY,
            **self.build_params(image_url, safe_search=safe_search),
        }
        if self.supports_safe_search:
            params["safe"] = "active" if safe_search else "off"

        response = requests.get(SERPAPI_ENDPOINT, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()

        error_value = payload.get("error")
        if error_value:
            error_text = str(error_value).lower()
            if "returned any results" in error_text or "hasn't returned any" in error_text:
                return {}
            raise RuntimeError(str(error_value))

        return payload
