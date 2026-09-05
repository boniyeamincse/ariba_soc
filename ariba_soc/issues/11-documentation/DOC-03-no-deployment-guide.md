# DOC-03: No Deployment Guide

- **Severity**: Medium
- **Priority**: P2 (next sprint)
- **Category**: Documentation

## Current Problem
There are no deployment instructions for any environment:
- No production checklist
- No nginx configuration example
- No supervisor/systemd service file
- No SSL/TLS guidance
- No backup/restore instructions
- No monitoring setup guidance
- No log rotation configuration

A developer who sets up the app in dev mode has no guidance on how to make it production-ready.

## Expected Behavior
A `docs/deployment.md` document should cover:
1. Production requirements (Python, PostgreSQL, Redis, nginx)
2. System dependencies installation
3. Database setup and migration
4. Static files collection and serving (whitenoise or nginx)
5. Gunicorn + systemd service configuration
6. nginx reverse proxy configuration with SSL
7. Environment variable checklist
8. Logging configuration
9. Backup and restore procedures
10. Monitoring and alerting setup

## Affected Files
- `docs/deployment.md` (needs to be created)
- `deploy/nginx.conf` (example nginx config, needs to be created)
- `deploy/ariba-soc.service` (systemd service, needs to be created)

## Suggested Fix
Example nginx config (`deploy/nginx.conf`):
```nginx
server {
    listen 443 ssl;
    server_name soc.example.com;
    
    ssl_certificate /etc/ssl/certs/soc.example.com.pem;
    ssl_certificate_key /etc/ssl/private/soc.example.com.key;
    
    location /static/ {
        alias /var/www/ariba-soc/staticfiles/;
        expires 30d;
    }
    
    location /media/ {
        alias /var/www/ariba-soc/media/;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Example systemd service (`deploy/ariba-soc.service`):
```ini
[Unit]
Description=Ariba SOC Django Application
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=ariba-soc
WorkingDirectory=/var/www/ariba-soc
EnvironmentFile=/var/www/ariba-soc/.env
ExecStart=/var/www/ariba-soc/venv/bin/gunicorn -c gunicorn.conf.py config.wsgi:application
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## QA Verification
1. Follow the deployment guide on a fresh Ubuntu 22.04 server.
2. The complete deployment must succeed in < 30 minutes.
3. The deployed app must be accessible via HTTPS.
4. `/static/` and `/media/` must be served correctly.
5. Service must auto-restart on crash (`systemctl restart` test).
