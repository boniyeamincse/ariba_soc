# AW-005: Notification Settings Exist But No Delivery Logic

- **Severity**: High
- **Priority**: P1 (this sprint)
- **Category**: Alert Workflow

## Current Problem
`settings_manager/models.py:125-153` defines `NotificationSetting` with event types (NEW_CRITICAL, ALERT_ASSIGNED, SLA_BREACH, etc.) and channels (EMAIL, DASHBOARD, TEAMS). The settings UI fully supports creating notification rules. However, **no code anywhere delivers notifications**.

When events occur:
- A new critical alert is created → no email is sent
- An alert is assigned → no in-app or email notification
- SLA breaches → no alert
- The TEAMS integration channel is defined but never called

The only half-implemented notification is the "new alerts waiting" banner in `base.html:84-93`, which is based on a simple count query in the context processor.

## Expected Behavior
A notification service should evaluate active `NotificationSetting` rules on relevant events and deliver via the specified channel:
- **EMAIL**: Send via Django's `send_mail` (SMTP must be configured)
- **DASHBOARD**: Create an in-app notification model
- **TEAMS**: Send webhook to Microsoft Teams

## Affected Files
- `alerts/services.py` (needs notification call in `update_alert`, `assign_alert`, etc.)
- `wazuh_integration/services.py:176` (needs notification on new alert creation)
- `alerts/models.py` (needs in-app Notification model)

## Suggested Fix
Create a notification service:
```python
# alerts/notification_service.py
from django.core.mail import send_mail
from settings_manager.models import NotificationSetting

def notify(event_type, alert, related_user=None):
    rules = NotificationSetting.objects.filter(event_type=event_type, is_active=True)
    for rule in rules:
        if rule.channel == 'EMAIL' and rule.recipient_email:
            send_mail(...)
        elif rule.channel == 'TEAMS':
            # Send Teams webhook
            pass
        elif rule.channel == 'DASHBOARD':
            # Create in-app notification
            InAppNotification.objects.create(...)
```

## QA Verification
1. Create a notification rule: event=NEW_CRITICAL, channel=DASHBOARD.
2. Import a Critical alert → an in-app notification must appear.
3. Create a rule with channel=EMAIL → an email must be sent (verify via console backend in dev).
