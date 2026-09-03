import re

with open('frontend/next.config.js', 'r') as f:
    content = f.read()

strict_csp = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https://unsplash.com https://images.unsplash.com https://image.tmdb.org https://img.clerk.com https://images.clerk.dev; "
    "connect-src 'self' https://cineiq.com wss://cineiq.com ws://localhost:* http://localhost:*; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self';"
)

content = re.sub(
    r"key:\s*'Content-Security-Policy',\s*value:\s*\"[^\"]*\"",
    f"key: 'Content-Security-Policy',\n            value: \"{strict_csp}\"",
    content
)

with open('frontend/next.config.js', 'w') as f:
    f.write(content)
