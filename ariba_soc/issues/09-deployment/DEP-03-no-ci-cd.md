# DEP-03: No CI/CD Pipeline Configuration

- **Severity**: Medium
- **Priority**: P2 (next sprint)
- **Category**: Deployment

## Current Problem
There are no CI/CD configuration files:
- No GitHub Actions `.yml` files
- No GitLab CI `.gitlab-ci.yml`
- No pre-commit hooks for linting
- No automated test runner on push/PR

Every code change must be manually tested and deployed. There's no automated quality gate.

## Expected Behavior
A GitHub Actions workflow should be created that:
1. Runs on push to `main` and on all PRs
2. Runs `pip install -r requirements.txt`
3. Runs `python manage.py test` (see TST-001)
4. Runs `python manage.py check --deploy` for security checks
5. Runs `ruff` or `flake8` for linting
6. (Optional) Runs `python manage.py makemigrations --check` to verify migrations

## Affected Files
- `.github/workflows/ci.yml` (needs to be created)
- `.github/workflows/deploy.yml` (needs to be created)

## Suggested Fix
```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: ariba_soc_test
          POSTGRES_USER: ariba_soc
          POSTGRES_PASSWORD: ariba_soc
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python manage.py test
        env:
          DATABASE_ENGINE: django.db.backends.postgresql
          DATABASE_NAME: ariba_soc_test
          DATABASE_USER: ariba_soc
          DATABASE_PASSWORD: ariba_soc
          DATABASE_HOST: localhost
          DJANGO_SECRET_KEY: ci-test-key-not-for-production
          DJANGO_DEBUG: 'False'
```

## QA Verification
1. Push the CI file to GitHub.
2. Verify the CI action triggers automatically.
3. All steps must pass (lint, test, check, migration check).
