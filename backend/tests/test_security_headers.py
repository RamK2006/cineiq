from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.core.security import CSP_DIRECTIVES, ALLOWED_ORIGINS

client = TestClient(app)

def test_security_headers_present():
    """Verify that all strict OWASP security headers are returned on standard requests."""
    response = client.get("/health")
    assert response.status_code in (200, 503)
    
    headers = response.headers
    assert "Content-Security-Policy" in headers
    assert headers["Content-Security-Policy"] == CSP_DIRECTIVES
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert headers.get("X-XSS-Protection") == "1; mode=block"

def test_hsts_header_in_production():
    """Strict-Transport-Security should only be included in production environments."""
    with patch("app.main.ENV", "production"):
        response = client.get("/health")
        assert "Strict-Transport-Security" in response.headers
        assert "max-age=31536000" in response.headers["Strict-Transport-Security"]
        assert "includeSubDomains" in response.headers["Strict-Transport-Security"]

def test_cors_preflight_headers():
    """Verify CORS OPTIONS preflight returns appropriate allow-headers."""
    response = client.options("/health", headers={
        "Origin": "https://cineiq.com",
        "Access-Control-Request-Method": "GET"
    })
    
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://cineiq.com"
    assert "access-control-allow-credentials" in response.headers
    assert response.headers["access-control-allow-credentials"] == "true"

def test_cors_rejects_disallowed_origin():
    """CORS middleware should not echo back disallowed origins."""
    response = client.get("/health", headers={
        "Origin": "https://evil-hacker-site.com"
    })
    
    # Origin is not in ALLOWED_ORIGINS, so allow-origin shouldn't be the evil site
    assert response.headers.get("access-control-allow-origin") != "https://evil-hacker-site.com"

def test_allowed_origins_no_wildcard():
    """Ensure that we aren't using dangerous wildcards with credentials enabled."""
    assert "*" not in ALLOWED_ORIGINS
    for origin in ALLOWED_ORIGINS:
        assert origin.startswith("http")
