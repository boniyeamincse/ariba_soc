# Configuration Guide

## Environment Variables (.env)

All configuration is managed via a `.env` file using `python-decouple`.

### Django Core

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEBUG` | Yes | `False` | Django debug mode (`True`/`False`) |
| `SECRET_KEY` | Yes | — | Django secret key (generate with `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`) |
| `ALLOWED_HOSTS` | No | `localhost,127.0.0.1` | Comma-separated allowed hosts |
| `USE_SQLITE` | No | `False` | Use SQLite instead of PostgreSQL |

### Database (PostgreSQL)

| Variable | Required | Description |
|----------|----------|-------------|
| `DB_NAME` | Yes (if not SQLite) | Database name |
| `DB_USER` | Yes | Database user |
| `DB_PASSWORD` | Yes | Database password |
| `DB_HOST` | Yes | Database host |
| `DB_PORT` | No | Database port (default: 5432) |

### Wazuh Manager API

| Variable | Required | Description |
|----------|----------|-------------|
| `WAZUH_MANAGER_URL` | Yes | Base URL (e.g., `https://10.24.66.2:55000`) |
| `WAZUH_MANAGER_USER` | Yes | API username with administrator role |
| `WAZUH_MANAGER_PASSWORD` | Yes | API user password |

### Wazuh Indexer API

| Variable | Required | Description |
|----------|----------|-------------|
| `WAZUH_INDEXER_URL` | Yes | Base URL (e.g., `https://10.24.66.2:9200`) |
| `WAZUH_INDEXER_USER` | Yes | OpenSearch username |
| `WAZUH_INDEXER_PASSWORD` | Yes | OpenSearch password |

### Email (Optional)

| Variable | Description |
|----------|-------------|
| `EMAIL_HOST` | SMTP server host |
| `EMAIL_PORT` | SMTP port (default: 587) |
| `EMAIL_HOST_USER` | SMTP username |
| `EMAIL_HOST_PASSWORD` | SMTP password |
| `EMAIL_USE_TLS` | Use TLS (default: True) |
| `DEFAULT_FROM_EMAIL` | From address |

## Django Settings (`config/settings.py`)

### Installed Apps

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'alerts',
    'audit',
    'dashboard',
    'reports',
    'settings_manager',
    'wazuh_integration',
]
```

### Middleware

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'audit.middleware.AuditMiddleware',  # Custom audit logging
]
```

### Database Router

SQLite config (dev):
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

PostgreSQL config (production):
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', default='5432'),
        'OPTIONS': {'sslmode': 'require'},
    }
}
```

## Runtime Settings (Settings Manager)

In addition to `.env`, the `settings_manager` app manages runtime configuration:

| Setting Key | Type | Default | Purpose |
|-------------|------|---------|---------|
| `SLA_HOURS` | int | 24 | Hours allowed before SLA breach |
| `MAX_ESCALATIONS_PER_ALERT` | int | 3 | Max escalation chain length |
| `AUTO_ESCALATE_AFTER_HOURS` | int | 48 | Auto-escalate if idle |
| `NOTIFY_ON_ASSIGN` | bool | True | Send notification on assignment |
| `NOTIFY_ON_ESCALATION` | bool | True | Send notification on escalation |
| `NOTIFY_EMAIL` | str | — | Email address for notifications |
