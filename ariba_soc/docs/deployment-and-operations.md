# Deployment & Operations

## Production Architecture

```
┌─────────┐     :443     ┌──────────┐    :8091    ┌──────────┐    :5432    ┌────────────┐
│ Browser  │ ──────────→ │  Nginx   │ ──────────→ │ Gunicorn │ ──────────→ │ PostgreSQL │
└─────────┘              └──────────┘             └──────────┘             └────────────┘
                              │                          │
                              │                    ┌─────┴──────┐
                              │                    │  Static    │
                              │                    │  Files     │
                              │                    └────────────┘
                              │
                         ┌────┴────┐
                         │  SSL    │
                         │  Certs  │
                         └─────────┘
```

## Nginx Configuration (`deploy/nginx.conf`)

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/ssl/certs/ariba-soc.crt;
    ssl_certificate_key /etc/ssl/private/ariba-soc.key;

    client_max_body_size 100M;

    location /static/ {
        alias /opt/ariba_soc/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:8091;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Gunicorn Service (`deploy/ariba-soc.service`)

```ini
[Unit]
Description=Ariba SOC Gunicorn Service
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/ariba_soc
EnvironmentFile=/opt/ariba_soc/.env
ExecStart=/opt/ariba_soc/venv/bin/gunicorn \
    --bind 127.0.0.1:8091 \
    --workers 3 \
    --timeout 120 \
    --access-logfile /var/log/ariba-soc/access.log \
    --error-logfile /var/log/ariba-soc/error.log \
    config.wsgi:application
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Docker Deployment (`deploy/docker-compose.yml`)

```yaml
version: '3.8'
services:
  web:
    build: ..
    ports:
      - "8091:8091"
    env_file: ../.env
    depends_on:
      - db
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: ariba_soc
      POSTGRES_USER: ariba_soc
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
volumes:
  postgres_data:
```

## Operations Tasks

### Start / Stop / Restart

```bash
sudo systemctl start ariba-soc
sudo systemctl stop ariba-soc
sudo systemctl restart ariba-soc
sudo systemctl status ariba-soc
```

### Logs

```bash
# Application logs
sudo journalctl -u ariba-soc -f
sudo tail -f /var/log/ariba-soc/access.log
sudo tail -f /var/log/ariba-soc/error.log

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Database Management

```bash
# Backup
pg_dump -U ariba_soc ariba_soc > backup_$(date +%Y%m%d).sql

# Restore
psql -U ariba_soc ariba_soc < backup.sql

# Migrations
python manage.py migrate
python manage.py showmigrations
```

### Static Files

```bash
# After any CSS/JS changes
python manage.py collectstatic --noinput
```

### Monitoring Checklist

- [ ] Gunicorn service is running: `systemctl status ariba-soc`
- [ ] Nginx is running: `systemctl status nginx`
- [ ] PostgreSQL is running: `systemctl status postgresql`
- [ ] Disk space: `df -h`
- [ ] Logs show no errors: `journalctl -u ariba-soc --since "1 hour ago"`
- [ ] Test endpoint returns 200: `curl -k https://localhost:8091/`
- [ ] Wazuh connections healthy: Test via UI

### SSL Certificate Renewal

```bash
sudo certbot renew --nginx
```

## Health Check Endpoint

`GET /` returns the dashboard page (200 OK) if the app is healthy.

Consider adding a dedicated health check:

```python
# config/urls.py
from django.http import JsonResponse

urlpatterns += [
    path('api/health/', lambda r: JsonResponse({'status': 'ok'})),
]
```
