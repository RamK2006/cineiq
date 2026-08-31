import io
import structlog
import httpx
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException, Query, Response
from typing import Optional
import collections
from PIL import Image, UnidentifiedImageError
import ipaddress

logger = structlog.get_logger()
router = APIRouter(prefix="/images", tags=["images"])

class BoundedCache:
    def __init__(self, maxsize: int = 500):
        self.cache = collections.OrderedDict()
        self.maxsize = maxsize

    def get(self, key: str) -> Optional[bytes]:
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def put(self, key: str, value: bytes) -> None:
        self.cache[key] = value
        self.cache.move_to_end(key)
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)

image_cache = BoundedCache(maxsize=500)

def is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        
        hostname = parsed.hostname
        if not hostname:
            return False
            
        if hostname in ("localhost", "127.0.0.1", "::1"):
            return False
            
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return False
        except ValueError:
            pass
            
        return True
    except Exception:
        return False

@router.get("/proxy")
async def proxy_image(
    url: str = Query(..., description="External image URL"),
    w: int = Query(..., gt=0, le=2000, description="Requested output width"),
    q: int = Query(..., ge=1, le=100, description="Requested image quality")
):
    """Proxy an external image, resize it, and convert to WebP."""
    if not is_safe_url(url):
        raise HTTPException(status_code=400, detail="Invalid or unsafe URL")

    cache_key = f"{url}_{w}_{q}"
    cached_img = image_cache.get(cache_key)
    
    if cached_img:
        logger.info("image_cache_hit", url=url, width=w, quality=q)
        return Response(
            content=cached_img,
            media_type="image/webp",
            headers={"Cache-Control": "public, max-age=604800"}
        )

    logger.info("image_cache_miss", url=url, width=w, quality=q)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10.0, follow_redirects=True)
            resp.raise_for_status()
            content = resp.content
            
            # Simple size limit check (e.g. 10MB) to prevent large downloads from consuming memory
            if len(content) > 10 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="Image too large")

    except httpx.RequestError as e:
        logger.error("image_proxy_download_failed", url=url, error=str(e))
        raise HTTPException(status_code=502, detail="Failed to download external image")
    except httpx.HTTPStatusError as e:
        logger.error("image_proxy_http_error", url=url, status_code=e.response.status_code)
        raise HTTPException(status_code=502, detail="External image returned error status")

    try:
        img = Image.open(io.BytesIO(content))
        
        # Avoid decompression bomb attacks
        if img.width > 10000 or img.height > 10000:
            raise HTTPException(status_code=400, detail="Image dimensions too large")
            
        # Calculate new height preserving aspect ratio
        aspect_ratio = img.height / img.width
        new_height = int(w * aspect_ratio)
        
        # Resize
        # Use LANCZOS for high-quality downsampling
        img = img.resize((w, new_height), Image.Resampling.LANCZOS)
        
        # Convert to WebP format
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")
            
        out_bytes = io.BytesIO()
        img.save(out_bytes, format="WEBP", quality=q)
        webp_data = out_bytes.getvalue()
        
        # Cache the result
        image_cache.put(cache_key, webp_data)
        
        return Response(
            content=webp_data,
            media_type="image/webp",
            headers={"Cache-Control": "public, max-age=604800"}
        )
        
    except UnidentifiedImageError:
        logger.error("image_proxy_invalid_content", url=url)
        raise HTTPException(status_code=400, detail="Unsupported or invalid image content")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("image_proxy_processing_failed", url=url, error=str(e))
        raise HTTPException(status_code=500, detail="Image processing failed")
