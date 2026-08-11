# Security Documentation

## Authentication

- **Session-based auth** with Django's built-in authentication
- **Password hashing:** Django's default PBKDF2 with SHA-256
- **Session security:** CSRF tokens on all forms, session expiry on browser close
- **Login required:** All views decorated with `@login_required`
- **No API tokens exposed in client-side code**

## Authorization

- **Role-based access control** via `@role_required` decorator
- **4 role tiers:** Admin > Manager > L2 Analyst > L1 Analyst
- **Template-level gating:** Navigation items hidden based on role
- **Model-level checks:** Views check `request.user.analystprofile.role` before mutation
- **Delegation control:** L1 can only change own alerts; L2/Manager/Admin can change any

## Credential Storage

- **Wazuh credentials** stored in environment variables (`.env`), never in the database or VCS
- **Database credentials** stored in environment variables
- **Django `SECRET_KEY`** stored in environment variables
- **Email SMTP credentials** stored in environment variables
- **Wazuh Manager/Indexer passwords** read from `.env` at runtime via `python-decouple`

## Network Security

```
Internet → HTTPS :443 → Nginx → proxy_pass :8091 → Django → PostgreSQL (localhost:5432)
                                                         → Wazuh Manager :55000 (internal network)
                                                         → Wazuh Indexer :9200 (internal network)
```

- **Nginx** terminates SSL/TLS
- **Django** runs behind Nginx, not exposed directly
- **PostgreSQL** bound to localhost, not exposed to network
- **Wazuh** connections are HTTPS with SSL verification disabled (self-signed certs)
- **`DEBUG=False`** in production — disables debug error pages

## Audit Logging

| Log Source | Captures | Retention |
|------------|----------|-----------|
| `AuditMiddleware` | Every HTTP request (user, action, model, object, IP, timestamp) | Indefinite |
| `AlertAuditLog` | Alert status changes, assignments, escalations | Indefinite |
| `SettingAuditLog` | Configuration changes | Indefinite |
| `WazuhSyncLog` | Sync operations (fetched, created, skipped, errors) | Indefinite |

## Input Validation

- **Django forms** validate all user input (ModelForms with field validation)
- **CSRF protection** on all POST endpoints
- **Content-type checks** on file uploads
- **XSS protection:** Django template auto-escaping enabled
- **SQL injection:** Django ORM parameterized queries

## HTTPS Configuration (Nginx)

```nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/ssl/certs/ariba-soc.crt;
    ssl_certificate_key /etc/ssl/private/ariba-soc.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ...
}
```

## Security Headers

Recommended Nginx headers (included in `deploy/nginx.conf`):
```nginx
add_header X-Frame-Options "DENY";
add_header X-Content-Type-Options "nosniff";
add_header X-XSS-Protection "1; mode=block";
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
```

## Best Practices Checklist

- [x] Debug disabled in production
- [x] Secret key in environment variable
- [x] Database credentials in environment variable
- [x] HTTPS enforced at Nginx level
- [x] CSRF protection on all forms
- [x] Session-based auth with HttpOnly cookies
- [x] Role-based access on every view
- [x] Audit logging for all sensitive actions
- [x] No hardcoded credentials in code
- [x] `.env` in `.gitignore`
- [x] PostgreSQL not exposed externally
- [x] SSL/TLS for Wazuh connections
