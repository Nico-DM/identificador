from unittest.mock import patch

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestHealthRoutes:
    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["persistence"] in ("memory", "supabase")
        assert isinstance(data["file_upload"], bool)

    def test_request_id_header(self):
        response = client.get("/health", headers={"X-Request-ID": "test-req-123"})
        assert response.headers.get("X-Request-ID") == "test-req-123"


class TestSearchRoutes:
    def test_search_invalid_url(self):
        response = client.post(
            "/api/search",
            json={"image_url": "not-a-url"},
        )
        assert response.status_code == 400
        assert "code" in response.json()

    def test_search_invalid_extension(self):
        response = client.post(
            "/api/search",
            json={"image_url": "https://example.com/file.pdf"},
        )
        assert response.status_code == 400

    def test_get_results_not_found(self):
        response = client.get("/api/results/nonexistent-id")
        assert response.status_code == 404

    def test_deep_search_not_found(self):
        response = client.post("/api/search/nonexistent-id/deep")
        assert response.status_code == 404

    @patch("routes.search.start_search")
    def test_search_valid_url(self, mock_start):
        mock_start.return_value = {"search_id": "test-id", "status": "processing"}
        response = client.post(
            "/api/search",
            json={"image_url": "https://example.com/photo.jpg"},
        )
        assert response.status_code == 200
        assert response.json()["search_id"] == "test-id"
        mock_start.assert_called_once()

    @patch("routes.search.search_get")
    def test_deep_search_wrong_status(self, mock_get):
        mock_get.return_value = {
            "status": "processing",
            "deep_search_available": False,
        }
        response = client.post("/api/search/some-id/deep")
        assert response.status_code == 400
