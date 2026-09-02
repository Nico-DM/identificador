from search_engines.utils import is_http_url


class TestIsHttpUrl:
    def test_valid_http(self):
        assert is_http_url("http://example.com") is True

    def test_valid_https(self):
        assert is_http_url("https://example.com/path") is True

    def test_invalid_scheme(self):
        assert is_http_url("ftp://example.com") is False

    def test_missing_host(self):
        assert is_http_url("https://") is False

    def test_empty_string(self):
        assert is_http_url("") is False
