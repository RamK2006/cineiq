import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import ALLOWED_ORIGINS, CSP_DIRECTIVES

client = TestClient(app)

def test_security_headers_present():
    response = client.get("/health")
    assert response.status_code in (200, 503)
    
    headers = response.headers
    assert "Content-Security-Policy" in headers
    assert headers["Content-Security-Policy"] == CSP_DIRECTIVES
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert headers.get("X-XSS-Protection") == "1; mode=block"


def test_cors_preflight():
    response = client.options(
        "/health",
        headers={
            "Origin": "https://cineiq.com",
            "Access-Control-Request-Method": "GET",
        }
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://cineiq.com"
    assert response.headers.get("access-control-allow-credentials") == "true"
