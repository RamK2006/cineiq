from fastapi.testclient import TestClient
from app.main import app

def test_protected_endpoint_without_token_fails():
    """Verify that accessing protected endpoints without auth token returns 401/403 or 503."""
    client = TestClient(app)
    response = client.get("/api/v1/profile/stats")
    assert response.status_code in (401, 403, 503)

def test_room_create_unauthenticated_fails():
    """Verify that creating a watch room without auth token returns 401/403 or 503."""
    client = TestClient(app)
    response = client.post("/api/v1/room/create")
    assert response.status_code in (401, 403, 503)
