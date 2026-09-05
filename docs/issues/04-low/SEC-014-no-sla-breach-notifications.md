# SEC-014: No SLA breach notifications

**Severity:** Low  
**Priority:** P3  
**Category:** Missing Feature  
**Status:** Open  
**File:** `ariba_soc/alerts/`

## Current Problem
SLA system tracks breaches (`sla_status='Breached'`) but no automated notification when SLA is breached. `NotificationSetting` has `SLA_BREACH` event type but no code creates notifications.

## Expected Behavior
Automated notification when SLA is breached.

## Affected Files
- `ariba_soc/alerts/services.py`
- `ariba_soc/alerts/signals.py`

## Suggested Fix
```python
# In alert save/signal handler
def check_sla_breach(alert):
    if alert.sla_status == 'Breached' and not alert.sla_breach_notified:
        # Create notification
        Notification.objects.create(
            user=alert.assignee or get_soc_manager(),
            message=f"SLA breached for alert: {alert.alert_name}",
            link=f'/alerts/{alert.id}/',
            notification_type='SLA_BREACH'
        )
        alert.sla_breach_notified = True
        alert.save(update_fields=['sla_breach_notified'])
```

## QA Verification
- Alert SLA breaches → notification created
- Assignee receives in-app notification
