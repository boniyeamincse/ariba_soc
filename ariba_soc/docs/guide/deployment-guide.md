# Deployment Guide

## 1. Production Architecture Overview
- **Web Server:** Nginx
- **WSGI Server:** Gunicorn
- **Database:** PostgreSQL
- **Process Manager:** Systemd or Docker Compose

## 2. Gunicorn Setup
Install Gunicorn inside your virtual environment.
```bash
pip install gunicorn
```
Run Gunicorn:
```bash
gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3
```

## 3. Nginx Configuration
Create a server block for Ariba SOC:
```nginx
server {
    listen 80;
    server_name soc.yourdomain.com;

    location /static/ {
        alias /path/to/ariba_soc/staticfiles/;
    }

    location /media/ {
        alias /path/to/ariba_soc/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 4. Static Files
Ensure you collect static files before going live.
```bash
python manage.py collectstatic --noinput
```
