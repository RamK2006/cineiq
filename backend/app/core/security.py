"""
backend/app/core/security.py
----------------------------
Refactored security and authentication module for CineIQ utilizing Clerk JWKS and strict validation.
"""

from __future__ import annotations

import os
from typing import Any, List, Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import httpx
import structlog
import time

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Read configuration from environment variables with production fallbacks
ENV: str = os.getenv("ENV", os.getenv("ENVIRONMENT", "production")).lower()

# Strict whitelist configuration (Prohibiting wildcards with credentials in production)
ALLOWED_ORIGINS: List[str] = [
    "https://cineiq.com",
    "https://www.cineiq.com",
]

if ENV not in ("production", "prod"):
    ALLOWED_ORIGINS.extend(["http://localhost:3000", "http://127.0.0.1:3000"])

# Strict CSP Directive configuration
CSP_DIRECTIVES: str = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https://unsplash.com https://images.unsplash.com https://image.tmdb.org; "
    "connect-src 'self' https://cineiq.com; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; report-uri /api/v1/security/csp-report;"
)

security = HTTPBearer(auto_error=False)

# Simple dictionary cache with timestamp since cachetools was removed
_jwks_cache: dict[str, Any] = {"data": None, "expires_at": 0}


async def get_jwks() -> Optional[dict[str, Any]]:
    """Retrieve and cache Clerk JWKS keys securely."""
    global _jwks_cache
    now = time.time()

    if _jwks_cache["data"] and _jwks_cache["expires_at"] > now:
        return _jwks_cache["data"]

    if not settings.clerk_secret_key or "REPLACE" in settings.clerk_secret_key:
        return None

    try:
        jwks_url = "https://api.clerk.com/v1/jwks"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                jwks_url,
                headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
            )
            if resp.status_code == 200:
                jwks = resp.json()
                _jwks_cache = {"data": jwks, "expires_at": now + 3600}
                return jwks
    except Exception as e:
        logger.error("jwks_fetch_failed", error=str(e))
        return None
    return None


async def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict[str, Any]:
    """Verify and decode bearer tokens against Clerk JWKS with clock skew leeway and replay protection."""
    if not credentials:
        if not settings.clerk_secret_key or "REPLACE" in settings.clerk_secret_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    token = credentials.credentials

    if not settings.clerk_secret_key or "REPLACE" in settings.clerk_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    jwks = await get_jwks()
    if not jwks:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication configuration error",
        )

    try:
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks.get("keys", []):
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
                break

        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate key",
            )

        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key)
        audience = getattr(settings, "clerk_jwt_audience", None) or getattr(settings, "clerk_audience", None)
        
        decode_kwargs: dict[str, Any] = {"algorithms": ["RS256"]}
        if audience:
            decode_kwargs["audience"] = audience
            decode_kwargs["options"] = {"verify_aud": True}
        else:
            decode_kwargs["options"] = {"verify_aud": False}

        payload = jwt.decode(token, public_key, **decode_kwargs)

        # Replay protection and window validation (with leeway for clock skew)
        now = time.time()
        leeway = 5.0

        iat = payload.get("iat")
        if iat is not None and iat > (now + leeway):
            logger.warning("jwt_iat_in_future", iat=iat, now=now)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token issued in the future",
            )

        exp = payload.get("exp")
        if exp is not None and exp < (now - leeway):
            logger.warning("jwt_expired", exp=exp, now=now)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )

        return payload

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error("jwt_validation_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )


async def get_current_user(payload: dict[str, Any] = Depends(verify_token)) -> str:
    """Extract and validate the user sub claim from verified token payloads."""
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found in token")
    return user_id
