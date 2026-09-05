# CODE-007: gunicorn logs to non-existent directory

**Severity:** Low  
**Priority:** P3  
**Category:** Reliability  
**Status:** Open  
**File:** `ariba_soc/gunicorn.conf.py`

## Current Problem
`accesslog` and `errorlog` point to `/var/log/ariba-soc/` but Dockerfile doesn't create this directory.

## Expected Behavior
Either create directory in entrypoint or use stdout.

## Affected Files
- `ariba_soc/gunicorn.conf.py` (lines 8-9)
- `ariba_soc/docker/entrypoint.sh`

## Suggested Fix
```python
# gunicorn.conf.py - use stdout
accesslog = '-'
errorlog = '-'
```

Or add to entrypoint:
```bash
mkdir -p /var/log/ariba-soc/
chown appuser:appuser /var/log/ariba-soc/
```

## QA Verification
- Gunicorn starts without errors
- Logs appear in Docker logs
