"""Tests for storage helpers and upload/delete with mocked HTTP."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import storage
from exceptions import ServiceUnavailableError, ValidationError

JPEG_BYTES = b"\xff\xd8\xff" + b"\x00" * 20
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
GIF_BYTES = b"GIF89a" + b"\x00" * 20
WEBP_BYTES = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 8
BMP_BYTES = b"BM" + b"\x00" * 20


class TestStorageEnabled:
    def test_disabled_without_creds(self, monkeypatch):
        monkeypatch.setattr(storage, "SUPABASE_URL", "")
        monkeypatch.setattr(storage, "SUPABASE_SERVICE_ROLE_KEY", "")
        assert storage.storage_enabled() is False

    def test_enabled_with_creds(self, monkeypatch):
        monkeypatch.setattr(storage, "SUPABASE_URL", "https://xyz.supabase.co")
        monkeypatch.setattr(storage, "SUPABASE_SERVICE_ROLE_KEY", "secret")
        assert storage.storage_enabled() is True


class TestDetectImageFormat:
    def test_jpeg(self):
        assert storage._detect_image_format(JPEG_BYTES) == ".jpg"

    def test_png(self):
        assert storage._detect_image_format(PNG_BYTES) == ".png"

    def test_gif(self):
        assert storage._detect_image_format(GIF_BYTES) == ".gif"

    def test_webp(self):
        assert storage._detect_image_format(WEBP_BYTES) == ".webp"

    def test_bmp(self):
        assert storage._detect_image_format(BMP_BYTES) == ".bmp"

    def test_unknown(self):
        assert storage._detect_image_format(b"not-an-image") is None


class TestValidateUpload:
    def test_empty_file(self):
        with pytest.raises(ValidationError, match="vacío"):
            storage.validate_upload(b"", "a.jpg")

    def test_too_large(self, monkeypatch):
        monkeypatch.setattr(storage, "UPLOAD_MAX_BYTES", 10)
        with pytest.raises(ValidationError, match="tamaño máximo"):
            storage.validate_upload(JPEG_BYTES, "a.jpg")

    def test_bad_extension(self):
        with pytest.raises(ValidationError, match="no permitido"):
            storage.validate_upload(JPEG_BYTES, "a.pdf")

    def test_not_image_content(self):
        with pytest.raises(ValidationError, match="no es una imagen"):
            storage.validate_upload(b"hello world!!!!!", "a.jpg")

    def test_extension_mismatch(self):
        with pytest.raises(ValidationError, match="no coincide"):
            storage.validate_upload(PNG_BYTES, "photo.jpg")

    def test_jpeg_jpg_jpeg_aliases(self):
        ext, ctype = storage.validate_upload(JPEG_BYTES, "photo.jpeg")
        assert ext == ".jpeg"
        assert ctype == "image/jpeg"

    def test_valid_png(self):
        ext, ctype = storage.validate_upload(PNG_BYTES, "shot.png")
        assert ext == ".png"
        assert ctype == "image/png"


class TestUploadAndDelete:
    def test_upload_requires_storage(self, monkeypatch):
        monkeypatch.setattr(storage, "SUPABASE_URL", "")
        monkeypatch.setattr(storage, "SUPABASE_SERVICE_ROLE_KEY", "")
        with pytest.raises(ServiceUnavailableError) as exc:
            storage.upload_search_image(JPEG_BYTES, "a.jpg")
        assert exc.value.code == "STORAGE_UNAVAILABLE"

    def test_upload_success(self, monkeypatch):
        monkeypatch.setattr(storage, "SUPABASE_URL", "https://xyz.supabase.co")
        monkeypatch.setattr(storage, "SUPABASE_SERVICE_ROLE_KEY", "secret")
        monkeypatch.setattr(storage, "STORAGE_BUCKET", "search-uploads")

        response = MagicMock()
        response.ok = True
        with patch("storage.requests.post", return_value=response) as post:
            public_url, path = storage.upload_search_image(JPEG_BYTES, "a.jpg")

        assert path.startswith("uploads/")
        assert path.endswith(".jpg")
        assert "search-uploads" in public_url
        post.assert_called_once()

    def test_upload_failure(self, monkeypatch):
        monkeypatch.setattr(storage, "SUPABASE_URL", "https://xyz.supabase.co")
        monkeypatch.setattr(storage, "SUPABASE_SERVICE_ROLE_KEY", "secret")
        response = MagicMock()
        response.ok = False
        response.status_code = 500
        response.text = "fail"
        with patch("storage.requests.post", return_value=response), pytest.raises(ServiceUnavailableError) as exc:
            storage.upload_search_image(JPEG_BYTES, "a.jpg")
        assert exc.value.code == "STORAGE_UPLOAD_FAILED"

    def test_delete_noop_when_disabled(self, monkeypatch):
        monkeypatch.setattr(storage, "SUPABASE_URL", "")
        monkeypatch.setattr(storage, "SUPABASE_SERVICE_ROLE_KEY", "")
        with patch("storage.requests.delete") as delete:
            storage.delete_search_image("uploads/x.jpg")
        delete.assert_not_called()

    def test_delete_success(self, monkeypatch):
        monkeypatch.setattr(storage, "SUPABASE_URL", "https://xyz.supabase.co")
        monkeypatch.setattr(storage, "SUPABASE_SERVICE_ROLE_KEY", "secret")
        response = MagicMock()
        response.ok = True
        with patch("storage.requests.delete", return_value=response) as delete:
            storage.delete_search_image("uploads/x.jpg")
        delete.assert_called_once()

    def test_delete_logs_on_http_error(self, monkeypatch):
        monkeypatch.setattr(storage, "SUPABASE_URL", "https://xyz.supabase.co")
        monkeypatch.setattr(storage, "SUPABASE_SERVICE_ROLE_KEY", "secret")
        response = MagicMock()
        response.ok = False
        response.status_code = 404
        with patch("storage.requests.delete", return_value=response):
            storage.delete_search_image("uploads/missing.jpg")

    def test_delete_logs_on_request_exception(self, monkeypatch):
        monkeypatch.setattr(storage, "SUPABASE_URL", "https://xyz.supabase.co")
        monkeypatch.setattr(storage, "SUPABASE_SERVICE_ROLE_KEY", "secret")
        import requests

        with patch(
            "storage.requests.delete",
            side_effect=requests.RequestException("network"),
        ):
            storage.delete_search_image("uploads/x.jpg")
