from env_util import env_str
from exceptions import ConfigurationError

from search_engines.base import SearchEngine
from search_engines.bing_visual import BingVisualEngine
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


def get_search_engine(engine_name: str | None = None) -> SearchEngine:
    """Return the configured reverse-image search strategy."""
    name = (engine_name or _DEFAULT_ENGINE).strip()
    engine_cls = _ENGINE_REGISTRY.get(name)
    if engine_cls is None:
        supported = ", ".join(sorted(_ENGINE_REGISTRY))
        raise ConfigurationError(
            f"Motor de búsqueda desconocido: {name!r}. Soportados: {supported}"
        )
    return engine_cls()


def registered_engines() -> tuple[str, ...]:
    return tuple(sorted(_ENGINE_REGISTRY))
