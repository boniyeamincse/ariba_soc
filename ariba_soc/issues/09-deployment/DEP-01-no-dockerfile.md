# DEP-01: No Dockerfile or Docker Compose Configuration

- **Severity**: High
- **Priority**: P1 (this sprint)
- **Category**: Deployment

## Current Problem
The project has no containerization:
- No `Dockerfile` for building the application image
- No `docker-compose.yml` for orchestrating Django, PostgreSQL, Redis
- No `.dockerignore`
- No environment variable templating for Docker secrets

This means every deployment requires manual setup of Python, PostgreSQL, Redis, and dependencies. There's no reproducible build artifact.

## Expected Behavior
A standard Docker setup should be provided:
- Multi-stage `Dockerfile` (builder → runner)
- `docker-compose.yml` with Django, PostgreSQL, Redis services
- `.dockerignore` excluding `__pycache__`, `.git`, etc.
- Health checks for all services

## Affected Files
- `Dockerfile` (needs to be created)
- `docker-compose.yml` (needs to be created)
- `.dockerignore` (needs to be created)

## Suggested Fix
```dockerfile
# Dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: ariba_soc
      POSTGRES_USER: ariba_soc
      POSTGRES_PASSWORD: ${DB_PASSWORD}
  redis:
    image: redis:7
  web:
    build: .
    ports: ["8000:8000"]
    depends_on: [db, redis]
    environment:
      DATABASE_ENGINE: django.db.backends.postgresql
      DATABASE_NAME: ariba_soc
      DATABASE_USER: ariba_soc
      DATABASE_PASSWORD: ${DB_PASSWORD}
      DATABASE_HOST: db
      REDIS_URL: redis://redis:6379/1
```

## QA Verification
1. Run `docker compose up --build` — all services must start.
2. Run `docker compose exec web python manage.py migrate` — migrations must apply.
3. Run `docker compose exec web python manage.py seed_alerts` — seed data must load.
4. Access http://localhost:8000 — the app must be fully functional.
