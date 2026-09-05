# CODE-003: scripts force SQLite in production

**Severity:** Medium  
**Priority:** P2  
**Category:** Code Quality  
**Status:** Open  
**File:** `ariba_soc/scripts/create_admin.py`

## Current Problem
`create_admin.py` sets `os.environ['DATABASE_ENGINE'] = 'django.db.backends.sqlite3'` which forces SQLite regardless of configured database.

## Expected Behavior
Scripts use whatever DB is configured in the environment.

## Affected Files
- `ariba_soc/scripts/create_admin.py` (line 7)

## Suggested Fix
```python
# Remove this line:
# os.environ['DATABASE_ENGINE'] = 'django.db.backends.sqlite3'

# Let the script use whatever DATABASE_ENGINE is in the environment
```

## QA Verification
- Run `create_admin.py` with PostgreSQL configured → uses PostgreSQL
- No SQLite override in any script
