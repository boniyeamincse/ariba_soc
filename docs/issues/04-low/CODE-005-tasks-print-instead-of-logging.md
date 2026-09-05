# CODE-005: tasks.py uses print() instead of logging

**Severity:** Low  
**Priority:** P3  
**Category:** Code Quality  
**Status:** Open  
**File:** `ariba_soc/wazuh_integration/tasks.py`

## Current Problem
`run_scheduled_sync` uses `print()` for output. In production, stdout may not be captured.

## Expected Behavior
Use `logging` module.

## Affected Files
- `ariba_soc/wazuh_integration/tasks.py` (lines 6-8)

## Suggested Fix
```python
import logging
logger = logging.getLogger(__name__)

def run_scheduled_sync():
    logger.info("Starting scheduled sync...")
    try:
        # ... sync logic
        logger.info(f"Sync completed: {result}")
    except Exception as e:
        logger.error(f"Sync failed: {e}")
```

## QA Verification
- Check application logs for sync messages
- No print() output in stdout
