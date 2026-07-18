import pytest
from unittest import mock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.security import verify_token, get_current_user

async def test_auth_development_bypass_no_credentials(monkeypatch):
    """Test that auth is bypassed and returns a dummy user in development with no credentials."""
    monkeypatch.setattr(settings, "clerk_secret_key", "")
    monkeypatch.setattr(settings, "environment", "development")
    
    payload = await verify_token(None)
    assert payload == {"sub": "dev_user_123", "role": "user"}

async def test_auth_development_bypass_with_credentials(monkeypatch):
    """Test that auth is bypassed and returns a dummy user in development even with credentials."""
    monkeypatch.setattr(settings, "clerk_secret_key", "")
    monkeypatch.setattr(settings, "environment", "development")
    
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="any_dummy_token")
    payload = await verify_token(credentials)
    assert payload == {"sub": "dev_user_123", "role": "user"}

async def test_auth_missing_credentials_in_production(monkeypatch):
    """Test that missing credentials in production environment returns 401."""
    monkeypatch.setattr(settings, "clerk_secret_key", "secret_clerk_key")
    monkeypatch.setattr(settings, "environment", "production")
    
    with pytest.raises(HTTPException) as excinfo:
        await verify_token(None)
    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Not authenticated"

async def test_auth_configuration_failure_no_jwks(monkeypatch):
    """Test 401 configuration error when JWKS retrieval fails in production."""
    monkeypatch.setattr(settings, "clerk_secret_key", "secret_clerk_key")
    monkeypatch.setattr(settings, "environment", "production")
    
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test_token")
    
    # Mock get_jwks to return None
    with mock.patch("app.core.security.get_jwks", return_value=None):
        with pytest.raises(HTTPException) as excinfo:
            await verify_token(credentials)
        assert excinfo.value.status_code == 401
        assert excinfo.value.detail == "Authentication configuration error"

async def test_auth_invalid_token(monkeypatch):
    """Test 401 invalid token when PyJWT decoding fails in production."""
    monkeypatch.setattr(settings, "clerk_secret_key", "secret_clerk_key")
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "clerk_audience", "")
    
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid_token")
    
    # Mock get_jwks to return keys
    mock_jwks = {
        "keys": [
            {
                "kid": "another_kid",
                "kty": "RSA",
                "use": "sig",
                "n": "test_n",
                "e": "AQAB"
            }
        ]
    }
    
    with mock.patch("app.core.security.get_jwks", return_value=mock_jwks):
        with pytest.raises(HTTPException) as excinfo:
            await verify_token(credentials)
        assert excinfo.value.status_code == 401
        assert "Invalid token" in excinfo.value.detail or "Unable to find appropriate key" in excinfo.value.detail

async def test_get_current_user_success():
    """Test retrieving user_id successfully from payload."""
    payload = {"sub": "user_id_12345", "role": "user"}
    user_id = await get_current_user(payload)
    assert user_id == "user_id_12345"

async def test_get_current_user_missing_sub():
    """Test retrieving user_id fails when 'sub' claim is missing."""
    payload = {"role": "user"}
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(payload)
    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "User ID not found in token"
