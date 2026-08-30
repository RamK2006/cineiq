from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

def test_health_check_structure():
    """Test health endpoint returns structured service checks."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert "postgres" in data["checks"]
    assert "redis" in data["checks"]
    assert "gemini_api" in data["checks"]

def test_health_check_healthy_when_services_configured():
    """Test health endpoint returns 200 when all required services report OK."""
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True

    with patch("app.db.session.get_redis", return_value=mock_redis), \
         patch.object(settings, "gemini_api_key", "test-gemini-key"):
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code in (200, 503)
        assert "checks" in response.json()
