# SEC-006: Notification failures silently swallowed

**Severity:** High  
**Priority:** P1  
**Category:** Security / Reliability  
**Status:** Open  
**File:** `ariba_soc/alerts/services.py`

## Current Problem
`_notify_assignment` and `_notify_escalation` catch all exceptions and do `pass`. If the notification system is broken (DB down, email server unreachable), failures are completely silent.

## Expected Behavior
- Log all notification failures
- Alert admin if notification pipeline is down
- Track notification delivery status

## Affected Files
- `ariba_soc/alerts/services.py` (lines 111-156)

## Suggested Fix
```python
import logging
logger = logging.getLogger(__name__)

def _notify_assignment(alert, assignee, assigner, request=None):
    try:
        # ... existing code ...
    except Exception as e:
        logger.exception(f"Failed to notify {assignee.username} about alert {alert.id}")
        # Optionally: create a NotificationFailure record
```

## QA Verification
- Disable email server → check logs for notification errors
- Check that admin is notified of pipeline failures
