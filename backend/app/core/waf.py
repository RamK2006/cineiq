import re
import urllib.parse
from typing import Callable, Awaitable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import structlog
import time
import json
from app.db.session import get_redis

logger = structlog.get_logger(__name__)

class WebApplicationFirewall:
    """
    A custom, highly-engineered Web Application Firewall (WAF).
    It intercepts incoming requests and scores them based on heuristic signatures
    (SQLi, XSS, Path Traversal). High threat scores result in dynamic IP blocking.
    """
    
    # Heuristic signature regex patterns
    SQLI_PATTERN = re.compile(r"(?i)(union\s+select|select\s+.*\s+from|insert\s+into|update\s+.*\s+set|delete\s+from|drop\s+table|--|\b1=1\b|xp_cmdshell)")
    XSS_PATTERN = re.compile(r"(?i)(<script>|javascript:|onerror=|onload=|eval\(|document\.cookie|window\.location|alert\()")
    LFI_PATTERN = re.compile(r"(?i)(\.\./\.\./|etc/passwd|windows/win\.ini|/bin/sh|/bin/bash)")
    
    # Thresholds
    BLOCK_THRESHOLD = 100
    PENALTY_SQLI = 50
    PENALTY_XSS = 40
    PENALTY_LFI = 60
    
    def __init__(self):
        self.redis = get_redis()
        
    async def analyze_request(self, request: Request) -> int:
        """Analyzes a request and returns a threat score (0 = clean, >0 = suspicious)."""
        score = 0
        
        # 1. Analyze URI and Query Params
        raw_url = str(request.url)
        decoded_url = urllib.parse.unquote(raw_url)
        score += self._score_payload(decoded_url)
        
        # 2. Analyze Headers
        user_agent = request.headers.get("user-agent", "")
        if "sqlmap" in user_agent.lower() or "nikto" in user_agent.lower() or "curl" in user_agent.lower():
            score += 20  # Suspicious automated tooling
            
        # 3. Analyze Body (if accessible)
        # Note: Consuming the body in middleware can be tricky, we only check small JSON payloads
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    # We peek at the body safely
                    body = await request.body()
                    if body and len(body) < 10000:  # Only parse small bodies to prevent DoS
                        decoded_body = body.decode("utf-8", errors="ignore")
                        score += self._score_payload(decoded_body)
                except Exception:
                    pass
                    
        return score
        
    def _score_payload(self, payload: str) -> int:
        score = 0
        if self.SQLI_PATTERN.search(payload):
            score += self.PENALTY_SQLI
        if self.XSS_PATTERN.search(payload):
            score += self.PENALTY_XSS
        if self.LFI_PATTERN.search(payload):
            score += self.PENALTY_LFI
        return score
        
    def get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "127.0.0.1"
        
    def is_ip_blocked(self, ip: str) -> bool:
        if not self.redis:
            return False
        return self.redis.exists(f"waf:block:{ip}") == 1
        
    def add_threat_score(self, ip: str, score: int):
        if not self.redis or score == 0:
            return
            
        key = f"waf:score:{ip}"
        current_score = self.redis.incrby(key, score)
        
        # TTL for score is 1 hour
        if current_score == score:
            self.redis.expire(key, 3600)
            
        if current_score >= self.BLOCK_THRESHOLD:
            logger.warning("waf_ip_blocked", ip=ip, score=current_score)
            self.redis.setex(f"waf:block:{ip}", 86400, "Blocked by WAF heuristics") # 24 hour block

async def waf_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    waf = WebApplicationFirewall()
    ip = waf.get_client_ip(request)
    
    # Fast path: Check blocklist
    if waf.is_ip_blocked(ip):
        logger.warning("waf_rejected_request", ip=ip, reason="IP currently blocked")
        return JSONResponse(
            status_code=403, 
            content={"error": "Access Denied", "reason": "WAF Rules Triggered"}
        )
        
    # Analyze request for threats
    threat_score = await waf.analyze_request(request)
    if threat_score > 0:
        logger.info("waf_threat_detected", ip=ip, score=threat_score, path=request.url.path)
        waf.add_threat_score(ip, threat_score)
        
        if waf.is_ip_blocked(ip):
            return JSONResponse(
                status_code=403, 
                content={"error": "Access Denied", "reason": "WAF Rules Triggered"}
            )
            
    # Proceed
    response = await call_next(request)
    return response
