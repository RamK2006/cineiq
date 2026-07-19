import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import time

from app.core.config import settings

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
                headers={"Authorization": f"Bearer {settings.clerk_secret_key}"}
            )
            if resp.status_code == 200:
                jwks = resp.json()
                _jwks_cache = {
                    "data": jwks,
                    "expires_at": now + 3600 # 1 hour
                }
                return jwks
    except Exception as e:
        import logging
        logging.getLogger("uvicorn").error(f"Failed to fetch JWKS: {e}")
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
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
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
            detail="Authentication configuration error"
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
                    "e": key["e"]
                }
                break

        if rsa_key:
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key)
            
            options = {}
            if settings.clerk_audience:
                options["verify_aud"] = True
            else:
                options["verify_aud"] = False

            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=settings.clerk_audience if settings.clerk_audience else None,
                options=options
            )
            return payload
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unable to find appropriate key"
    )

async def get_current_user(payload: dict = Depends(verify_token)):
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in token")
    return user_id
