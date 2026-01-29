"""Tests for FastAPI endpoints."""

from fastapi.testclient import TestClient

from ru_corrector.app import app

# Initialize test client (app as positional argument)
client = TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self):
        """Test GET /health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestCorrectEndpoint:
    """Test text correction endpoint with new API contract."""

    def test_correct_basic(self):
        """Test basic correction request."""
        response = client.post("/correct", json={"text": "Простой текст для проверки"})
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "edits" in data
        assert "stats" in data
        assert isinstance(data["edits"], list)

    def test_correct_mode_base(self):
        """Test correction in base mode."""
        response = client.post("/correct", json={"text": "Простой текст", "mode": "base"})
        assert response.status_code == 200
        data = response.json()
        assert "result" in data

    def test_correct_mode_legal(self):
        """Test correction in legal mode (default)."""
        response = client.post("/correct", json={"text": 'Он сказал "привет"'})
        assert response.status_code == 200
        data = response.json()
        # Legal mode should convert quotes
        assert "«" in data["result"] or "привет" in data["result"]

    def test_correct_mode_strict(self):
        """Test correction in strict mode."""
        response = client.post("/correct", json={"text": "Текст   с   пробелами", "mode": "strict"})
        assert response.status_code == 200
        data = response.json()
        assert "result" in data

    def test_correct_with_edits(self):
        """Test correction with return_edits=true."""
        response = client.post(
            "/correct", json={"text": 'Текст "в кавычках"', "return_edits": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert "edits" in data
        assert isinstance(data["edits"], list)

    def test_correct_without_edits(self):
        """Test correction with return_edits=false."""
        response = client.post(
            "/correct", json={"text": "Простой текст", "return_edits": False}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["edits"] == []

    def test_correct_stats(self):
        """Test that stats are returned correctly."""
        response = client.post("/correct", json={"text": "Простой текст"})
        assert response.status_code == 200
        data = response.json()
        stats = data["stats"]
        assert "chars_count" in stats
        assert "edits_count" in stats
        assert "processing_time_ms" in stats
        assert stats["chars_count"] > 0
        assert stats["processing_time_ms"] > 0

    def test_correct_empty_text(self):
        """Test with empty text (should fail validation)."""
        response = client.post("/correct", json={"text": ""})
        assert response.status_code == 422  # Validation error

    def test_correct_missing_text(self):
        """Test with missing text field."""
        response = client.post("/correct", json={})
        assert response.status_code == 422  # Validation error

    def test_request_id_header(self):
        """Test that request ID is added to response headers."""
        response = client.post("/correct", json={"text": "Тест"})
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

    def test_correct_quotes_conversion(self):
        """Test that legal mode converts quotes."""
        response = client.post(
            "/correct", json={"text": 'Он сказал "привет" и ушёл', "mode": "legal"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "«привет»" in data["result"]

    def test_correct_dash_conversion(self):
        """Test that legal mode converts dashes."""
        response = client.post(
            "/correct", json={"text": "Москва-Питер", "mode": "legal"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "—" in data["result"]

    def test_correct_ellipsis(self):
        """Test that typography converts ellipsis."""
        response = client.post("/correct", json={"text": "Привет... как дела"})
        assert response.status_code == 200
        data = response.json()
        assert "…" in data["result"]


class TestAPIDocumentation:
    """Test API documentation endpoints."""

    def test_openapi_schema(self):
        """Test OpenAPI schema is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema

    def test_docs_available(self):
        """Test that documentation is available."""
        response = client.get("/docs")
        assert response.status_code == 200
