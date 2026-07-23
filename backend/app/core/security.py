import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import time
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

security = HTTPBearer(auto_error=False)

# Simple dictionary cache with timestamp since cachetools was removed
_jwks_cache = {"data": None, "expires_at": 0}


async def get_jwks():
    global _jwks_cache
    now = time.time()

    if _jwks_cache["data"] and _jwks_cache["expires_at"] > now:
        return _jwks_cache["data"]

    # Simple workaround if no key provided
    if not settings.clerk_secret_key or "REPLACE" in settings.clerk_secret_key:
        return None

    # Derive JWKS URL from publishable key
    try:
        jwks_url = "https://api.clerk.com/v1/jwks"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                jwks_url,
                headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
            )
            if resp.status_code == 200:
                jwks = resp.json()
                _jwks_cache = {"data": jwks, "expires_at": now + 3600}  # 1 hour
                return jwks
    except Exception as e:
        logger.error("jwks_fetch_failed", error=str(e))
        return None


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        # If no credentials but we're in dev/test, return dummy user
        if not settings.clerk_secret_key or "REPLACE" in settings.clerk_secret_key:
            if settings.environment == "development":
                return {"sub": "dev_user_123", "role": "user"}
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    token = credentials.credentials

    # If no valid keys, allow bypass for development/testing
    if not settings.clerk_secret_key or "REPLACE" in settings.clerk_secret_key:
        if settings.environment == "development":
            return {"sub": "dev_user_123", "role": "user"}
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable"
        )

    jwks = await get_jwks()
    if not jwks:
        # Fallback if JWKS unavailable but keys are set - reject
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

        if rsa_key:
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key)

            audience = settings.clerk_jwt_audience or settings.clerk_audience
            decode_kwargs = {"algorithms": ["RS256"]}
            if audience:
                decode_kwargs["audience"] = audience
                decode_kwargs["options"] = {"verify_aud": True}
            else:
                decode_kwargs["options"] = {"verify_aud": False}

            payload = jwt.decode(token, public_key, **decode_kwargs)
            return payload

    except Exception as e:
        logger.error("jwt_validation_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unable to find appropriate key",
    )


async def get_current_user(payload: dict = Depends(verify_token)):
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in token")
    return user_id
