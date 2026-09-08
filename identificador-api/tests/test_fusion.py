from search_engines.base import SearchEngine, SearchOutcome
from search_engines.fused_engine import FusedSearchEngine
from search_engines.fusion import (
    is_low_quality_url,
    merge_outcomes,
    should_run_fallbacks,
)


class StubEngine(SearchEngine):
    def __init__(self, name: str, urls: list[str]):
        self._name = name
        self._urls = urls

    @property
    def name(self) -> str:
        return self._name

    def search(self, image_url: str, *, safe_search: bool = True) -> SearchOutcome:
        return SearchOutcome(urls=self._urls, match_metadata={}, raw_payload={})


class TestFusionHelpers:
    def test_should_run_fallbacks_when_below_threshold(self):
        assert should_run_fallbacks(0, min_urls=3) is True
        assert should_run_fallbacks(2, min_urls=3) is True
        assert should_run_fallbacks(3, min_urls=3) is False

    def test_filters_google_redirect_urls(self):
        assert is_low_quality_url(
            "https://www.google.com/goto?url=https://example.com"
        )

    def test_merge_outcomes_rrf_prefers_urls_in_multiple_engines(self):
        google = SearchOutcome(
            urls=["https://en.wikipedia.org/wiki/Mona_Lisa", "https://pinterest.com/pin/1"],
            match_metadata={},
            raw_payload={},
        )
        yandex = SearchOutcome(
            urls=["https://en.wikipedia.org/wiki/Mona_Lisa", "https://knowyourmeme.com/meme"],
            match_metadata={},
            raw_payload={},
        )
        merged = merge_outcomes([("google_reverse_image", google), ("yandex_images", yandex)])
        assert merged.urls[0] == "https://en.wikipedia.org/wiki/Mona_Lisa"
        assert "https://pinterest.com/pin/1" in merged.urls


class TestFusedSearchEngine:
    def test_skips_fallback_when_primary_has_enough_urls(self):
        primary = StubEngine("google_reverse_image", ["https://a.com", "https://b.com", "https://c.com"])
        fallback = StubEngine("yandex_images", ["https://fallback.com"])
        engine = FusedSearchEngine(primary, [fallback], min_urls_before_fallback=3)

        outcome = engine.search("https://example.com/image.jpg")
        assert outcome.urls == primary._urls
        assert engine.name == "fusion:google_reverse_image+yandex_images"

    def test_runs_fallback_when_primary_is_sparse(self):
        primary = StubEngine("google_reverse_image", [])
        fallback = StubEngine("yandex_images", ["https://en.wikipedia.org/wiki/Test"])
        engine = FusedSearchEngine(primary, [fallback], min_urls_before_fallback=3)

        outcome = engine.search("https://example.com/image.jpg")
        assert outcome.urls == ["https://en.wikipedia.org/wiki/Test"]
