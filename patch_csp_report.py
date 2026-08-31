import re

with open('frontend/next.config.js', 'r') as f:
    content = f.read()

# Add report-uri
content = content.replace("form-action 'self';", "form-action 'self'; report-uri /api/v1/security/csp-report;")
# Same in backend test
with open('backend/tests/test_security_headers.py', 'r') as f:
    test_content = f.read()

test_content = test_content.replace("form-action 'self';", "form-action 'self'; report-uri /api/v1/security/csp-report;")

with open('frontend/next.config.js', 'w') as f:
    f.write(content)
with open('backend/tests/test_security_headers.py', 'w') as f:
    f.write(test_content)
