# Testing Guide

## Test Framework

Ariba SOC uses Django's built-in `unittest`-based test framework with `pytest` compatibility.

## Running Tests

### All Tests

```bash
python manage.py test
```

### Specific App

```bash
python manage.py test accounts
python manage.py test alerts
python manage.py test dashboard
python manage.py test wazuh_integration
```

### Verbose Output

```bash
python manage.py test -v 2
```

### Run a Specific Test

```bash
python manage.py test wazuh_integration.tests.WazuhIntegrationTests.test_manager_config_creation
```

## Test Suite Overview

| Test Class | App | Tests | What It Covers |
|------------|-----|-------|----------------|
| `WazuhIntegrationTests` | `wazuh_integration` | 19 | Manager config CRUD, Indexer config CRUD, test connection views, permissions, sync flow, URL resolution |

## Test Configuration

Tests use SQLite in-memory database by default (no PostgreSQL required for unit tests).

CI pipeline (`./github/workflows/ci.yml`) runs tests against PostgreSQL 15:

```yaml
services:
  postgres:
    image: postgres:15
    env:
      POSTGRES_DB: ariba_soc
      POSTGRES_USER: ariba_soc
      POSTGRES_PASSWORD: ariba_soc_test
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5

steps:
  - run: pip install -r requirements.txt
  - run: python manage.py test
    env:
      DB_NAME: ariba_soc
      DB_USER: ariba_soc
      DB_PASSWORD: ariba_soc_test
      DB_HOST: localhost
      DB_PORT: '5432'
```

## Writing Tests

### Pattern

```python
from django.test import TestCase
from django.urls import reverse

class MyFeatureTests(TestCase):
    def setUp(self):
        """Create test users, data, and login."""
        self.admin = User.objects.create_superuser(
            username='admin', password='admin123'
        )
        self.client.login(username='admin', password='admin123')

    def test_feature_works(self):
        """Test description."""
        response = self.client.get(reverse('my-view'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'expected content')
```

### Key Test Utilities

- `self.client.login()` — authenticate test client
- `self.client.post(url, data)` — POST with CSRF token handling
- `reverse('view-name')` — resolve URL by name
- `assertContains(response, text)` — check response content
- `assertRedirects(response, url)` — check redirect

## Test Coverage Areas

| Area | Priority | Status |
|------|----------|--------|
| Wazuh Manager config CRUD | Critical | ✅ |
| Wazuh Indexer config CRUD | Critical | ✅ |
| Test connection endpoints | Critical | ✅ |
| Force sync flow | High | ✅ |
| Permission enforcement | High | ✅ |
| URL resolution | Medium | ✅ |
| Alert CRUD | High | ✅ |
| Alert board view | Medium | ✅ |
| Dashboard stats | Medium | ✅ |
| Report generation | Medium | ❌ |
| Audit logging | Medium | ❌ |
| Notification system | Low | ❌ |
| Settings manager | Low | ❌ |

## CI Pipeline

GitHub Actions workflow (`.github/workflows/ci.yml`):
- Trigger: push to `main`, pull requests
- Python 3.10
- PostgreSQL 15 service container
- Run `python manage.py test`
- Fail on test failure
