from unittest import mock
from app.core.config import settings

def test_health_success(client, monkeypatch):
    """Test health check success when both required services are healthy."""
    monkeypatch.setattr(settings, "gemini_api_key", "test_gemini_key")
    
    mock_redis_client = mock.MagicMock()
    mock_redis_client.ping.return_value = True
    monkeypatch.setattr("app.db.session.get_redis", lambda: mock_redis_client)
    
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["checks"]["redis"]["status"] == "ok"
    assert data["checks"]["gemini_api"]["status"] == "configured"
    assert "X-Request-ID" in response.headers

def test_health_not_configured_redis(client, monkeypatch):
    """Test health check status 503 when Redis is not configured."""
    monkeypatch.setattr(settings, "gemini_api_key", "test_gemini_key")
    monkeypatch.setattr("app.db.session.get_redis", lambda: None)
    
    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_configured"
    assert data["checks"]["redis"]["status"] == "not_configured"
    assert data["checks"]["gemini_api"]["status"] == "configured"

def test_health_not_configured_gemini(client, monkeypatch):
    """Test health check status 503 when Gemini is not configured."""
    monkeypatch.setattr(settings, "gemini_api_key", "")
    
    mock_redis_client = mock.MagicMock()
    mock_redis_client.ping.return_value = True
    monkeypatch.setattr("app.db.session.get_redis", lambda: mock_redis_client)
    
    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_configured"
    assert data["checks"]["redis"]["status"] == "ok"
    assert data["checks"]["gemini_api"]["status"] == "not_configured"

def test_health_degraded_redis_error(client, monkeypatch):
    """Test health check status 200 (degraded) when Redis ping fails."""
    monkeypatch.setattr(settings, "gemini_api_key", "test_gemini_key")
    
    mock_redis_client = mock.MagicMock()
    mock_redis_client.ping.side_effect = Exception("Redis connection refused")
    monkeypatch.setattr("app.db.session.get_redis", lambda: mock_redis_client)
    
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["checks"]["redis"]["status"].startswith("error:")
    assert data["checks"]["gemini_api"]["status"] == "configured"

def test_health_response_structure_and_header(client, monkeypatch):
    """Test that response structure is valid and includes the X-Request-ID header."""
    monkeypatch.setattr(settings, "gemini_api_key", "test_gemini_key")
    
    mock_redis_client = mock.MagicMock()
    mock_redis_client.ping.return_value = True
    monkeypatch.setattr("app.db.session.get_redis", lambda: mock_redis_client)
    
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] is not None
    
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert "redis" in data["checks"]
    assert "gemini_api" in data["checks"]
    assert "status" in data["checks"]["redis"]
    assert "last_checked" in data["checks"]["redis"]
    assert "status" in data["checks"]["gemini_api"]
    assert "last_checked" in data["checks"]["gemini_api"]
