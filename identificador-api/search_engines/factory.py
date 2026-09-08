from env_util import env_str, parse_positive_int
from exceptions import ConfigurationError

from search_engines.base import SearchEngine
from search_engines.bing_visual import BingVisualEngine
from search_engines.fused_engine import FusedSearchEngine
from search_engines.google_lens import GoogleLensEngine
from search_engines.google_reverse_image import GoogleReverseImageEngine
from search_engines.yandex_images import YandexImagesEngine

_ENGINE_REGISTRY: dict[str, type[SearchEngine]] = {
    "google_reverse_image": GoogleReverseImageEngine,
    "google_lens": GoogleLensEngine,
    "bing_reverse_image": BingVisualEngine,
    "bing_visual": BingVisualEngine,
    "yandex_images": YandexImagesEngine,
}

_DEFAULT_ENGINE = env_str(
    "SEARCH_ENGINE",
    env_str("SERPAPI_ENGINE", "google_reverse_image"),
)


def _parse_fallback_engine_names() -> list[str]:
    raw = env_str("SEARCH_FALLBACK_ENGINES", "")
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _build_engine(name: str) -> SearchEngine:
    engine_cls = _ENGINE_REGISTRY.get(name)
    if engine_cls is None:
        supported = ", ".join(sorted(_ENGINE_REGISTRY))
        raise ConfigurationError(
            f"Motor de búsqueda desconocido: {name!r}. Soportados: {supported}"
        )
    return engine_cls()


def get_search_engine(engine_name: str | None = None) -> SearchEngine:
    """Return the configured reverse-image search strategy."""
    name = (engine_name or _DEFAULT_ENGINE).strip()
    engine = _build_engine(name)

    fallback_names = _parse_fallback_engine_names()
    if not fallback_names:
        return engine

    fallbacks: list[SearchEngine] = []
    for fallback_name in fallback_names:
        if fallback_name == name:
            continue
        fallbacks.append(_build_engine(fallback_name))

    if not fallbacks:
        return engine

    min_urls = parse_positive_int(
        env_str("SEARCH_MIN_URLS_BEFORE_FALLBACK"),
        3,
    )
    return FusedSearchEngine(
        engine,
        fallbacks,
        min_urls_before_fallback=min_urls,
    )


def registered_engines() -> tuple[str, ...]:
    return tuple(sorted(_ENGINE_REGISTRY))
