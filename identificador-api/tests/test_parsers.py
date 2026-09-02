from search_engines.parsers import (
    extract_bing_match_metadata,
    extract_bing_urls,
    extract_google_match_metadata,
    extract_google_urls,
    extract_yandex_match_metadata,
    extract_yandex_urls,
)


class TestGoogleParsers:
    def test_extract_urls_from_visual_matches(self):
        payload = {
            "visual_matches": [
                {"link": "https://example.com/page1"},
                {"link": "https://example.com/page2"},
            ]
        }
        urls = extract_google_urls(payload)
        assert "https://example.com/page1" in urls
        assert "https://example.com/page2" in urls

    def test_dedupes_urls(self):
        payload = {
            "visual_matches": [
                {"link": "https://example.com/page"},
                {"link": "https://example.com/page"},
            ]
        }
        urls = extract_google_urls(payload)
        assert urls.count("https://example.com/page") == 1

    def test_filters_non_http(self):
        payload = {
            "visual_matches": [
                {"link": "ftp://example.com/file"},
                {"link": "https://example.com/ok"},
            ]
        }
        urls = extract_google_urls(payload)
        assert urls == ["https://example.com/ok"]

    def test_metadata_with_thumbnail(self):
        payload = {
            "visual_matches": [
                {
                    "link": "https://example.com/page",
                    "thumbnail": "https://cdn.example.com/thumb.jpg",
                    "source": "Example Site",
                    "source_icon": "https://cdn.example.com/favicon.ico",
                }
            ]
        }
        meta = extract_google_match_metadata(payload)
        key = "https://example.com/page"
        assert key in meta or any("example.com" in k for k in meta)
        entry = next(iter(meta.values()))
        assert entry.get("thumbnail") == "https://cdn.example.com/thumb.jpg"
        assert entry.get("site_name") == "Example Site"

    def test_inline_image_thumbnail_fallback(self):
        payload = {
            "inline_images": [
                {
                    "link": "https://example.com/gallery",
                    "thumbnail": "https://cdn.example.com/inline.jpg",
                }
            ],
            "image_results": [
                {"link": "https://example.com/gallery", "source": "Gallery"},
            ],
        }
        meta = extract_google_match_metadata(payload)
        entry = next(iter(meta.values()))
        assert entry.get("thumbnail") == "https://cdn.example.com/inline.jpg"


class TestBingParsers:
    def test_extract_urls(self):
        payload = {
            "related_content": [
                {"link": "https://bing-result.com/page"},
            ]
        }
        urls = extract_bing_urls(payload)
        assert urls == ["https://bing-result.com/page"]

    def test_metadata(self):
        payload = {
            "related_content": [
                {
                    "link": "https://bing-result.com/page",
                    "thumbnail": "https://cdn.com/t.jpg",
                    "title": "Bing Page",
                }
            ]
        }
        meta = extract_bing_match_metadata(payload)
        entry = next(iter(meta.values()))
        assert entry.get("site_name") == "Bing Page"


class TestYandexParsers:
    def test_extract_urls(self):
        payload = {
            "image_results": [
                {"link": "https://yandex-result.com/img"},
            ],
            "similar_images": [
                {"link": "https://yandex-result.com/similar"},
            ],
        }
        urls = extract_yandex_urls(payload)
        assert len(urls) == 2

    def test_metadata(self):
        payload = {
            "image_results": [
                {
                    "link": "https://yandex.com/page",
                    "original_image": "https://cdn.com/orig.jpg",
                    "title": "Yandex Result",
                }
            ]
        }
        meta = extract_yandex_match_metadata(payload)
        entry = next(iter(meta.values()))
        assert entry.get("site_name") == "Yandex Result"
