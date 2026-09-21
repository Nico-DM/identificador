"""Tests for dynamic_scraper helpers and extractors (Selenium mocked)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import dynamic_scraper as dyn
from selenium.common.exceptions import WebDriverException
from tests.helpers import utc_dt


class TestToNaiveUtc:
    def test_none(self):
        assert dyn._to_naive_utc(None) is None

    def test_aware(self):
        aware = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        naive = dyn._to_naive_utc(aware)
        assert naive is not None
        assert naive.tzinfo is None
        assert naive.hour == 12

    def test_already_naive(self):
        naive = utc_dt(2024, 1, 1, 8)
        assert dyn._to_naive_utc(naive) == naive


class TestTryParseDate:
    def test_iso(self):
        parsed = dyn._try_parse_date("2024-06-15T12:00:00Z")
        assert parsed is not None
        assert parsed.year == 2024

    def test_invalid(self):
        assert dyn._try_parse_date("not-a-date-xxx") is None


class TestAddCandidate:
    def test_skips_none(self):
        candidates: list = []
        dyn._add_candidate(candidates, None, "time", "", "https://x.com")
        assert candidates == []

    def test_appends(self):
        candidates: list = []
        dyn._add_candidate(
            candidates, utc_dt(2024, 2, 1), "time", "2024-02-01", "https://x.com"
        )
        assert len(candidates) == 1
        assert candidates[0].extractor == "dynamic"
        assert candidates[0].source == "time"


class FakeElement:
    def __init__(self, attrs: dict[str, str], text: str = ""):
        self._attrs = attrs
        self.text = text

    def get_attribute(self, name: str) -> str | None:
        return self._attrs.get(name)


class FakeDriver:
    def __init__(
        self,
        page_source: str,
        elements_by_selector: dict[str, list[FakeElement]] | None = None,
    ):
        self.page_source = page_source
        self._elements = elements_by_selector or {}
        self.quit_called = False

    def find_elements(self, _by: Any, selector: str) -> list[FakeElement]:
        return self._elements.get(selector, [])

    def get(self, _url: str) -> None:
        return None

    def set_page_load_timeout(self, _timeout: int) -> None:
        return None

    def execute_cdp_cmd(self, _cmd: str, _params: dict[str, Any]) -> None:
        return None

    def execute_script(self, _script: str) -> None:
        return None

    def quit(self) -> None:
        self.quit_called = True


class TestExtractFromDom:
    def test_time_and_meta(self):
        driver = FakeDriver(
            "<html><body></body></html>",
            {
                "time[datetime]": [
                    FakeElement({"datetime": "2023-04-05T10:00:00Z"}),
                ],
                "meta[property='article:published_time']": [
                    FakeElement({"content": "2023-04-01"}),
                ],
            },
        )
        candidates = dyn.extract_from_dom(driver, "https://example.com/post")
        assert len(candidates) >= 2
        assert any(c.source == "time" for c in candidates)
        assert any(c.source == "meta" for c in candidates)

    def test_selector_webdriver_error_continues(self):
        driver = MagicMock()
        driver.find_elements.side_effect = WebDriverException("boom")
        assert dyn.extract_from_dom(driver, "https://x.com") == []


class TestExtractFromScripts:
    def test_ld_json_date_published(self):
        html = """
        <html><body>
        <script type="application/ld+json">
        {"@type":"Article","datePublished":"2022-08-10T00:00:00Z"}
        </script>
        </body></html>
        """
        driver = FakeDriver(html)
        candidates = dyn.extract_dates_from_scripts(driver, "https://example.com")
        assert any(c.source == "ld+json" for c in candidates)

    def test_skips_cookie_scripts(self):
        html = """
        <html><body>
        <script>document.cookie = "x=1; expires=Thu, 01 Jan 2030"</script>
        </body></html>
        """
        driver = FakeDriver(html)
        assert dyn.extract_dates_from_scripts(driver, "https://example.com") == []

    def test_inline_json_keys(self):
        html = """
        <html><body>
        <script>
        var data = {"datePublished":"2021-01-02T03:04:05Z", "created_at":"2021-01-03"};
        </script>
        </body></html>
        """
        driver = FakeDriver(html)
        candidates = dyn.extract_dates_from_scripts(driver, "https://example.com")
        assert len(candidates) >= 1


class TestExtractVisibleText:
    def test_finds_iso_and_verbose(self):
        html = """
        <html><body>
        <p>Publicado el 2020-05-01T12:00:00Z y también 15 enero 2019</p>
        </body></html>
        """
        driver = FakeDriver(html)
        candidates = dyn.extract_from_visible_text(driver, "https://example.com")
        assert len(candidates) >= 1


class TestFetchDynamicCandidates:
    def test_happy_path(self):
        html = """
        <html><body>
        <time datetime="2024-01-15T08:00:00Z"></time>
        <p>Posted 2024-01-15</p>
        </body></html>
        """
        fake_driver = FakeDriver(
            html,
            {"time[datetime]": [FakeElement({"datetime": "2024-01-15T08:00:00Z"})]},
        )

        with (
            patch("dynamic_scraper.webdriver.Chrome", return_value=fake_driver),
            patch("dynamic_scraper.WebDriverWait") as wait_cls,
            patch("dynamic_scraper.time.sleep"),
        ):
            wait_cls.return_value.until = MagicMock()
            candidates = dyn.fetch_dynamic_candidates(
                "https://example.com/post", headless=True, wait_for=1
            )

        assert len(candidates) >= 1
        assert fake_driver.quit_called is True

    def test_returns_empty_on_webdriver_error(self):
        fake_driver = MagicMock()
        fake_driver.get.side_effect = WebDriverException("fail")
        fake_driver.execute_cdp_cmd = MagicMock()
        fake_driver.set_page_load_timeout = MagicMock()
        fake_driver.quit = MagicMock()

        with (
            patch("dynamic_scraper.webdriver.Chrome", return_value=fake_driver),
            patch("dynamic_scraper.time.sleep"),
        ):
            assert dyn.fetch_dynamic_candidates("https://example.com") == []
        fake_driver.quit.assert_called_once()
