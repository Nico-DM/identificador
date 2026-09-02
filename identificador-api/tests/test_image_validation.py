from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import pytest
import requests
from exceptions import ValidationError
from image_validation import (
    path_image_extension,
    validate_image_url,
    verify_url_returns_image,
)


class TestPathImageExtension:
    def test_jpg_extension(self):
        parsed = urlparse("https://example.com/photo.jpg")
        assert path_image_extension(parsed) == ".jpg"

    def test_uppercase_normalized(self):
        parsed = urlparse("https://example.com/photo.PNG")
        assert path_image_extension(parsed) == ".png"

    def test_trailing_slash(self):
        parsed = urlparse("https://example.com/photo.webp/")
        assert path_image_extension(parsed) == ".webp"

    def test_no_extension(self):
        parsed = urlparse("https://example.com/image")
        assert path_image_extension(parsed) == ""


class TestValidateImageUrl:
    def test_valid_extension(self):
        url = "https://example.com/photo.jpg"
        assert validate_image_url(url) == url

    def test_invalid_scheme(self):
        with pytest.raises(ValidationError, match="http"):
            validate_image_url("ftp://example.com/photo.jpg")

    def test_invalid_extension(self):
        with pytest.raises(ValidationError, match="extension"):
            validate_image_url("https://example.com/file.pdf")

    def test_no_extension_triggers_verify(self):
        with patch("image_validation.verify_url_returns_image") as mock_verify:
            url = "https://example.com/image"
            result = validate_image_url(url)
            mock_verify.assert_called_once_with(url)
            assert result == url


class TestVerifyUrlReturnsImage:
    def test_head_success(self):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.headers = {"Content-Type": "image/jpeg"}
        mock_resp.close = MagicMock()

        with patch("image_validation.requests.head", return_value=mock_resp):
            verify_url_returns_image("https://example.com/img")

    def test_get_fallback_success(self):
        mock_head = MagicMock()
        mock_head.ok = False
        mock_head.close = MagicMock()

        mock_get = MagicMock()
        mock_get.headers = {"Content-Type": "image/png"}
        mock_get.close = MagicMock()

        with (
            patch("image_validation.requests.head", return_value=mock_head),
            patch("image_validation.requests.get", return_value=mock_get),
        ):
            verify_url_returns_image("https://example.com/img")

    def test_network_error_raises(self):
        with patch(
            "image_validation.requests.head",
            side_effect=requests.ConnectionError("fail"),
        ), patch(
            "image_validation.requests.get",
            side_effect=requests.ConnectionError("fail"),
        ), pytest.raises(ValidationError, match="red"):
            verify_url_returns_image("https://example.com/img")

    def test_non_image_content_type_raises(self):
        mock_head = MagicMock()
        mock_head.ok = True
        mock_head.headers = {"Content-Type": "text/html"}
        mock_head.close = MagicMock()

        mock_get = MagicMock()
        mock_get.headers = {"Content-Type": "text/html"}
        mock_get.close = MagicMock()

        with (
            patch("image_validation.requests.head", return_value=mock_head),
            patch("image_validation.requests.get", return_value=mock_get),
            pytest.raises(ValidationError, match="no es una imagen"),
        ):
            verify_url_returns_image("https://example.com/page")
