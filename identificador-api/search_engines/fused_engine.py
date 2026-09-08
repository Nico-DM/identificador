from logging_config import get_logger

from search_engines.base import SearchEngine, SearchOutcome
from search_engines.fusion import merge_outcomes, should_run_fallbacks

logger = get_logger(__name__)


class FusedSearchEngine(SearchEngine):
    """Primary engine with optional fallbacks when recall is low."""

    def __init__(
        self,
        primary: SearchEngine,
        fallbacks: list[SearchEngine],
        *,
        min_urls_before_fallback: int = 3,
    ) -> None:
        self._primary = primary
        self._fallbacks = fallbacks
        self._min_urls = min_urls_before_fallback

    @property
    def name(self) -> str:
        parts = [self._primary.name] + [engine.name for engine in self._fallbacks]
        return "fusion:" + "+".join(parts)

    def search(self, image_url: str, *, safe_search: bool = True) -> SearchOutcome:
        labeled: list[tuple[str, SearchOutcome]] = []

        primary_outcome = self._primary.search(image_url, safe_search=safe_search)
        labeled.append((self._primary.name, primary_outcome))

        if should_run_fallbacks(len(primary_outcome.urls), min_urls=self._min_urls):
            for engine in self._fallbacks:
                if engine.name == self._primary.name:
                    continue
                try:
                    outcome = engine.search(image_url, safe_search=safe_search)
                except Exception as exc:  # noqa: BLE001 - continue with other engines
                    logger.warning(
                        "Fallback engine failed",
                        extra={
                            "event": "fallback_engine_failed",
                            "engine": engine.name,
                            "error": str(exc),
                        },
                    )
                    continue
                labeled.append((engine.name, outcome))
                logger.info(
                    "Fallback engine returned URLs",
                    extra={
                        "event": "fallback_engine_results",
                        "engine": engine.name,
                        "url_count": len(outcome.urls),
                    },
                )

        if len(labeled) == 1:
            return primary_outcome

        merged = merge_outcomes(labeled)
        logger.info(
            "Fused engine results",
            extra={
                "event": "engine_fusion_done",
                "primary_count": len(primary_outcome.urls),
                "merged_count": len(merged.urls),
                "engines_used": [name for name, _ in labeled],
            },
        )
        return merged
