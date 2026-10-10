from unittest.mock import MagicMock, patch

from static_scraper import (
    _extract_ld_json_dates,
    extract_candidate_dates,
    extract_htmldate,
    fetch_static_candidates,
)

SAMPLE_HTML = """
<html>
<head>
  <script type="application/ld+json">
  {"@type": "Article", "datePublished": "2024-03-15T10:00:00Z"}
  </script>
  <meta property="article:published_time" content="2024-02-01T08:00:00Z" />
</head>
<body>
  <time datetime="2024-01-20">20 de enero de 2024</time>
  <p>Publicado el 5 de marzo de 2023</p>
</body>
</html>
"""


class TestExtractHtmldate:
    def test_finds_publication_date(self):
        found = extract_htmldate(SAMPLE_HTML, url="https://example.com/article")
        assert found is not None
        assert found.startswith("2024-")

    def test_returns_none_on_empty_html(self):
        assert extract_htmldate("<html></html>") is None


class TestFetchStaticCandidates:
    @patch("static_scraper.requests.get")
    def test_htmldate_is_first_candidate(self, mock_get):
        response = MagicMock()
        response.status_code = 200
        response.text = SAMPLE_HTML
        mock_get.return_value = response

        candidates = fetch_static_candidates("https://example.com/article")
        assert candidates
        assert candidates[0].source == "htmldate"
        assert candidates[0].extractor == "static"
        assert any(c.source == "ld+json" for c in candidates)


class TestExtractCandidateDates:
    def test_finds_ld_json_date(self):
        dates = extract_candidate_dates(SAMPLE_HTML)
        sources = [source for _, source in dates]
        assert "ld+json" in sources

    def test_finds_meta_date(self):
        dates = extract_candidate_dates(SAMPLE_HTML)
        sources = [source for _, source in dates]
        assert "meta" in sources

    def test_finds_time_tag(self):
        dates = extract_candidate_dates(SAMPLE_HTML)
        sources = [source for _, source in dates]
        assert "time" in sources

    def test_finds_plain_text_spanish(self):
        dates = extract_candidate_dates(SAMPLE_HTML)
        texts = [text for text, _ in dates]
        assert any("marzo" in t.lower() for t in texts)


class TestExtractLdJsonDates:
    def test_nested_structure(self):
        from bs4 import BeautifulSoup

        html = """
        <script type="application/ld+json">
        [{"@type": "VideoObject", "uploadDate": "2023-12-01"}]
        </script>
        """
        soup = BeautifulSoup(html, "html.parser")
        dates = _extract_ld_json_dates(soup)
        assert any(source == "ld+json" for _, source in dates)

    def test_invalid_json_skipped(self):
        from bs4 import BeautifulSoup

        html = '<script type="application/ld+json">{invalid}</script>'
        soup = BeautifulSoup(html, "html.parser")
        dates = _extract_ld_json_dates(soup)
        assert dates == []
