"""Tests for FastAPI endpoints."""
import pytest
from fastapi.testclient import TestClient

from ru_corrector.app import app

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
    """Test text correction endpoint."""
    
    def test_correct_basic(self):
        """Test basic correction request."""
        response = client.post(
            "/correct",
            json={"text": "Простой текст для проверки"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "original" in data
        assert "corrected" in data
        assert "stats" in data
        assert data["diff"] is None
    
    def test_correct_with_diff(self):
        """Test correction with diff view."""
        response = client.post(
            "/correct",
            json={
                "text": "Простой текст",
                "show_diff": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["diff"] is not None
        assert isinstance(data["diff"], str)
    
    def test_correct_different_modes(self):
        """Test correction in different modes."""
        text = "Простой текст для проверки"
        for mode in ["min", "biz", "acad"]:
            response = client.post(
                "/correct",
                json={"text": text, "mode": mode}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["original"] == text
    
    def test_correct_with_quotes(self):
        """Test correction with quotes."""
        response = client.post(
            "/correct",
            json={"text": 'Он сказал "привет"'}
        )
        assert response.status_code == 200
        data = response.json()
        assert "«" in data["corrected"] or "привет" in data["corrected"]
    
    def test_correct_with_ellipsis(self):
        """Test correction with ellipsis."""
        response = client.post(
            "/correct",
            json={"text": "Привет... как дела"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "…" in data["corrected"]
    
    def test_correct_stats(self):
        """Test that stats are returned correctly."""
        response = client.post(
            "/correct",
            json={"text": "Простой текст"}
        )
        assert response.status_code == 200
        data = response.json()
        stats = data["stats"]
        assert "length" in stats
        assert "changes" in stats
        assert "processing_time_ms" in stats
        assert stats["length"] > 0
        assert stats["processing_time_ms"] > 0
    
    def test_correct_empty_text(self):
        """Test with empty text (should fail validation)."""
        response = client.post(
            "/correct",
            json={"text": ""}
        )
        assert response.status_code == 422  # Validation error
    
    def test_correct_too_long_text(self):
        """Test with text exceeding max length."""
        long_text = "a" * 20000  # More than MAX_TEXT_LEN (15000)
        response = client.post(
            "/correct",
            json={"text": long_text}
        )
        assert response.status_code == 422  # Validation error
    
    def test_correct_missing_text(self):
        """Test with missing text field."""
        response = client.post(
            "/correct",
            json={}
        )
        assert response.status_code == 422  # Validation error
    
    def test_request_id_header(self):
        """Test that request ID is added to response headers."""
        response = client.post(
            "/correct",
            json={"text": "Тест"}
        )
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers


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
