import secrets
import hmac
import hashlib
from typing import Callable, Awaitable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import structlog
from app.core.config import settings

logger = structlog.get_logger(__name__)

class CSRFTokenEngine:
    """
    Abstracts cryptographic generation and validation of CSRF tokens 
    using the Double Submit Cookie pattern.
    """
    
    # Ideally stored securely in env vars
    SECRET_KEY = getattr(settings, "secret_key", "super-secret-csrf-key-for-dev")
    
    @classmethod
    def generate_token(cls) -> str:
        """Generates a cryptographically secure random token."""
        raw_token = secrets.token_hex(32)
        signature = hmac.new(
            cls.SECRET_KEY.encode(),
            raw_token.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{raw_token}.{signature}"
        
    @classmethod
    def validate_token(cls, token: str) -> bool:
        """Validates the signature of a given token."""
        if not token or "." not in token:
            return False
            
        parts = token.split(".")
        if len(parts) != 2:
            return False
            
        raw_token, signature = parts
        expected_signature = hmac.new(
            cls.SECRET_KEY.encode(),
            raw_token.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)


async def csrf_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """
    Middleware that enforces CSRF validation on all state-mutating requests (POST, PUT, DELETE, PATCH).
    It checks if the token in the `X-CSRF-Token` header matches the cryptographically signed token.
    """
    method = request.method
    path = request.url.path
    
    # Exclude safe methods and webhooks from CSRF checks
    safe_methods = {"GET", "OPTIONS", "HEAD"}
    excluded_paths = ["/api/v1/security/csp-report"]
    
    if method not in safe_methods and not any(path.startswith(ep) for ep in excluded_paths):
        # Enforce CSRF
        client_token = request.headers.get("x-csrf-token")
        
        if not client_token or not CSRFTokenEngine.validate_token(client_token):
            logger.warning("csrf_validation_failed", path=path, method=method, ip=request.client.host if request.client else "unknown")
            return JSONResponse(
                status_code=403,
                content={"error": "CSRF Token missing or invalid."}
            )

    # Process request
    response = await call_next(request)
    
    # Inject a fresh CSRF token cookie for the frontend to read and use
    if method == "GET":
        new_token = CSRFTokenEngine.generate_token()
        response.set_cookie(
            key="csrf_token",
            value=new_token,
            httponly=False, # Must be readable by frontend JS to place in header
            samesite="lax",
            secure=True,
            max_age=3600
        )
        
    return response
