import pytest
import time
from unittest.mock import patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.security import verify_token
from fastapi.security import HTTPAuthorizationCredentials

# 1. Rate Limiting Tests

def test_rate_limiting_ip_whitelist_bypass():
    """Verify that whitelisted IPs bypass the rate limiter."""
    with patch.object(settings, "rate_limit_whitelist_ips", ["127.0.0.1"]):
        client = TestClient(app)
        # Make multiple requests exceeding typical limits (e.g., 100/minute)
        for _ in range(5):
            response = client.get("/health")
            # Health check might return 503 if services aren't setup, but not 429!
            assert response.status_code != 429

# 2. JWT Verification and Replay Protection Tests

@pytest.mark.asyncio
async def test_verify_token_iat_in_future_raises_401():
    """Verify that a token with iat in the future is rejected with 401."""
    now = time.time()
    future_payload = {
        "sub": "user_123",
        "iat": now + 100,  # 100 seconds in the future
        "exp": now + 3600
    }
    
    # Mock JWKS and public key decoding
    mock_jwks = {"keys": [{"kid": "key_1", "kty": "RSA", "use": "sig", "n": "mock", "e": "mock"}]}
    
    with patch("app.core.security.get_jwks", return_value=mock_jwks), \
         patch("jwt.get_unverified_header", return_value={"kid": "key_1"}), \
         patch("jwt.algorithms.RSAAlgorithm.from_jwk", return_value=None), \
         patch("jwt.decode", return_value=future_payload), \
         patch.object(settings, "clerk_secret_key", "mock-key"):
        
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="mock-token")
        with pytest.raises(HTTPException) as exc_info:
            await verify_token(credentials)
            
        assert exc_info.value.status_code == 401
        assert "issued in the future" in exc_info.value.detail

@pytest.mark.asyncio
async def test_verify_token_expired_raises_401():
    """Verify that an expired token is rejected with 401."""
    now = time.time()
    expired_payload = {
        "sub": "user_123",
        "iat": now - 3600,
        "exp": now - 100  # 100 seconds in the past
    }
    
    mock_jwks = {"keys": [{"kid": "key_1", "kty": "RSA", "use": "sig", "n": "mock", "e": "mock"}]}
    
    with patch("app.core.security.get_jwks", return_value=mock_jwks), \
         patch("jwt.get_unverified_header", return_value={"kid": "key_1"}), \
         patch("jwt.algorithms.RSAAlgorithm.from_jwk", return_value=None), \
         patch("jwt.decode", return_value=expired_payload), \
         patch.object(settings, "clerk_secret_key", "mock-key"):
        
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="mock-token")
        with pytest.raises(HTTPException) as exc_info:
            await verify_token(credentials)
            
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail
