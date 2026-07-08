# TST-03: All test.py Files Are Empty Stubs

- **Severity**: Medium
- **Priority**: P2 (next sprint)
- **Category**: Testing

## Current Problem
All `tests.py` files in the project are essentially empty (either truly empty or contain only `from django.test import TestCase` with no test methods). Running `python manage.py test` completes in under 1 second because there are no tests to run.

Additionally:
- No `pytest` configuration (`pytest.ini` or `pyproject.toml` `[tool.pytest]`)
- No `coverage` configuration (`.coveragerc`)
- No test fixtures or factories
- No CI integration for test reporting

## Expected Behavior
Running `python manage.py test` should execute at least 50+ tests across all apps and take several seconds. A `pytest.ini` should be provided for alternative test runners.

## Affected Files
- `accounts/tests.py`
- `alerts/tests.py`
- `settings_manager/tests.py`
- `wazuh_integration/tests.py`
- `audit/tests.py`
- `dashboard/tests.py`
- `reports/tests.py`

## Suggested Fix
Create a `pytest.ini`:
```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = tests.py test_*.py
testpaths = accounts alerts settings_manager wazuh_integration audit dashboard reports
```

Add to `requirements-dev.txt`:
```
pytest>=8.0
pytest-django>=4.8
pytest-cov>=5.0
factory-boy>=3.3
```

## QA Verification
1. Run `pytest` — must discover and run all test files.
2. Run `pytest --cov=. --cov-report=term` — must show coverage percentage (even if 0% currently).
3. After writing tests (per TST-01), the same command must show >20% coverage.
