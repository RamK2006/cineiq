import re

# 1. Update API router to include security router
with open('app/api/v1/__init__.py', 'r') as f:
    api_init = f.read()

if "security_router" not in api_init:
    api_init = "from app.api.v1.security_router import router as security_router\n" + api_init
    api_init += "\napi_router.include_router(security_router)\n"
    with open('app/api/v1/__init__.py', 'w') as f:
        f.write(api_init)

# 2. Update main.py to include WAF and CSRF middleware
with open('app/main.py', 'r') as f:
    main_content = f.read()

if "waf_middleware" not in main_content:
    imports = "from app.core.waf import waf_middleware\nfrom app.core.csrf import csrf_middleware\nfrom starlette.middleware.base import BaseHTTPMiddleware\n"
    main_content = imports + main_content
    
    # We add them below CORS
    middleware_hook = r"(app\.add_middleware\([\s\S]*?allow_headers=\[\"Content-Type\", \"Authorization\", \"X-Requested-With\"\],\n\))"
    
    add_middlewares = """
app.add_middleware(BaseHTTPMiddleware, dispatch=csrf_middleware)
app.add_middleware(BaseHTTPMiddleware, dispatch=waf_middleware)
"""
    
    main_content = re.sub(middleware_hook, r"\1" + "\n" + add_middlewares, main_content)
    
    with open('app/main.py', 'w') as f:
        f.write(main_content)
