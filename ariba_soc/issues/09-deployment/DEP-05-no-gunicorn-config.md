# DEP-05: No Gunicorn Configuration File

- **Severity**: Medium
- **Priority**: P2 (next sprint)
- **Category**: Deployment

## Current Problem
`config/settings.py` has `WSGI_APPLICATION = 'config.wsgi.application'` but there is no `gunicorn.conf.py` or documented gunicorn command for production deployment. The `config/wsgi.py` file exists but is standard Django boilerplate with no production tuning.

When deploying, an operator must guess the correct gunicorn settings:
- Number of workers
- Timeout values
- Logging configuration
- Graceful reload behavior

## Expected Behavior
A `gunicorn.conf.py` should be provided with:
- `workers = multiprocessing.cpu_count() * 2 + 1`
- `timeout = 120`
- `accesslog` and `errorlog` configuration
- `forwarded_allow_ips` for reverse proxy
- `reload = False` in production

## Affected Files
- `gunicorn.conf.py` (needs to be created)

## Suggested Fix
```python
"""Gunicorn configuration for Ariba SOC."""
import multiprocessing

bind = '0.0.0.0:8000'
workers = multiprocessing.cpu_count() * 2 + 1
timeout = 120
keepalive = 5

accesslog = '/var/log/ariba-soc/gunicorn-access.log'
errorlog = '/var/log/ariba-soc/gunicorn-error.log'
loglevel = 'info'

forwarded_allow_ips = '*'
proxy_protocol = False

reload = False
preload_app = True

worker_class = 'sync'
worker_connections = 1000
```

## QA Verification
1. Run `gunicorn -c gunicorn.conf.py config.wsgi:application`.
2. Verify server starts with the correct number of workers.
3. Verify log files are created at the specified paths.
4. Send a request — must return 200.
