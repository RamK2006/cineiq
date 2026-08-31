from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
import io
from PIL import Image

client = TestClient(app)

def create_test_image(width=100, height=100, color="red"):
    img = Image.new("RGB", (width, height), color=color)
    out = io.BytesIO()
    img.save(out, format="JPEG")
    return out.getvalue()

def test_image_proxy_success():
    """Test successful image proxy and conversion to WebP."""
    test_img_bytes = create_test_image(width=200, height=100)
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = test_img_bytes
        # raise_for_status is not async in httpx
        mock_resp.raise_for_status = MagicMock()
        
        # AsyncMock for the async method
        from unittest.mock import AsyncMock
        mock_get.side_effect = AsyncMock(return_value=mock_resp)

        response = client.get("/api/v1/images/proxy", params={"url": "https://example.com/image.jpg", "w": 100, "q": 80})
        
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "image/webp"
        assert response.headers["Cache-Control"] == "public, max-age=604800"
        
        # Verify it's a valid WebP image and resizing happened correctly
        img = Image.open(io.BytesIO(response.content))
        assert img.format == "WEBP"
        assert img.width == 100
        assert img.height == 50  # Aspect ratio preserved (200x100 -> 100x50)

def test_image_proxy_invalid_width():
    """Test validation error for invalid width."""
    response = client.get("/api/v1/images/proxy", params={"url": "https://example.com/image.jpg", "w": -10, "q": 80})
    assert response.status_code == 422
    
    response = client.get("/api/v1/images/proxy", params={"url": "https://example.com/image.jpg", "w": 3000, "q": 80})
    assert response.status_code == 422

def test_image_proxy_invalid_quality():
    """Test validation error for invalid quality."""
    response = client.get("/api/v1/images/proxy", params={"url": "https://example.com/image.jpg", "w": 100, "q": -1})
    assert response.status_code == 422
    
    response = client.get("/api/v1/images/proxy", params={"url": "https://example.com/image.jpg", "w": 100, "q": 200})
    assert response.status_code == 422

def test_image_proxy_invalid_url():
    """Test validation error for unsafe or invalid URL."""
    # Invalid URL scheme
    response = client.get("/api/v1/images/proxy", params={"url": "ftp://example.com/image.jpg", "w": 100, "q": 80})
    assert response.status_code == 400
    
    # Internal IP
    response = client.get("/api/v1/images/proxy", params={"url": "http://127.0.0.1/image.jpg", "w": 100, "q": 80})
    assert response.status_code == 400
    
    # Localhost
    response = client.get("/api/v1/images/proxy", params={"url": "http://localhost:8000/image.jpg", "w": 100, "q": 80})
    assert response.status_code == 400
    
    # Private IP
    response = client.get("/api/v1/images/proxy", params={"url": "http://192.168.1.5/image.jpg", "w": 100, "q": 80})
    assert response.status_code == 400

def test_image_proxy_upstream_failure():
    """Test handling of failed upstream request."""
    import httpx
    with patch("httpx.AsyncClient.get", side_effect=httpx.RequestError("Failed to connect")):
        response = client.get("/api/v1/images/proxy", params={"url": "https://example.com/fail.jpg", "w": 100, "q": 80})
        assert response.status_code == 502

def test_image_proxy_upstream_error_status():
    """Test handling of upstream error status codes."""
    import httpx
    from unittest.mock import AsyncMock
    
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_request = MagicMock()
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = AsyncMock(return_value=mock_resp)
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError("404 Not Found", request=mock_request, response=mock_resp)
        
        response = client.get("/api/v1/images/proxy", params={"url": "https://example.com/error.jpg", "w": 100, "q": 80})
        assert response.status_code == 502

def test_image_proxy_invalid_content():
    """Test handling of non-image content."""
    from unittest.mock import AsyncMock
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"not an image"
        mock_resp.raise_for_status = MagicMock()
        mock_get.side_effect = AsyncMock(return_value=mock_resp)

        response = client.get("/api/v1/images/proxy", params={"url": "https://example.com/notimage.txt", "w": 100, "q": 80})
        assert response.status_code == 400
        assert "unsupported" in response.json()["detail"].lower()

def test_image_proxy_caching():
    """Test that generated images are cached."""
    from unittest.mock import AsyncMock
    test_img_bytes = create_test_image(width=100, height=100)
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = test_img_bytes
        mock_resp.raise_for_status = MagicMock()
        mock_get.side_effect = AsyncMock(return_value=mock_resp)

        # First request should hit the mock
        response1 = client.get("/api/v1/images/proxy", params={"url": "https://example.com/cache.jpg", "w": 100, "q": 80})
        assert response1.status_code == 200
        assert mock_get.call_count == 1
        
        # Second request with same params should hit the cache
        response2 = client.get("/api/v1/images/proxy", params={"url": "https://example.com/cache.jpg", "w": 100, "q": 80})
        assert response2.status_code == 200
        assert mock_get.call_count == 1 # Still 1, so cache was hit
        
        # Third request with different params should miss the cache
        response3 = client.get("/api/v1/images/proxy", params={"url": "https://example.com/cache.jpg", "w": 150, "q": 80})
        assert response3.status_code == 200
        assert mock_get.call_count == 2
