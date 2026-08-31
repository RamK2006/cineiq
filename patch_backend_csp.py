with open('backend/app/core/security.py', 'r') as f:
    content = f.read()
content = content.replace("form-action 'self';", "form-action 'self'; report-uri /api/v1/security/csp-report;")
with open('backend/app/core/security.py', 'w') as f:
    f.write(content)
