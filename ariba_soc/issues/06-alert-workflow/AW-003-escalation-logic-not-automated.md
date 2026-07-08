# AW-003: Escalation Rules Defined But Never Executed

- **Severity**: High
- **Priority**: P1 (this sprint)
- **Category**: Alert Workflow

## Current Problem
`settings_manager/models.py:107-123` defines `EscalationRule` with fields for `severity_condition`, `alert_name_keyword`, `wazuh_rule_id`, `escalate_to_role`, and `escalate_to_user`. The settings UI fully supports creating these rules. However, **no code anywhere evaluates these rules**.

When a new alert is created (either via the seed command or Wazuh sync), the escalation rules are never checked. Alerts are never automatically escalated based on criteria. The only escalation path is manual via the `alert_escalate` view (`alerts/views.py:186-204`).

## Expected Behavior
When an alert is created or updated, a signal or service should:
1. Fetch all active `EscalationRule` records
2. Check if the alert matches any rule (by severity, keyword, and/or rule_id)
3. If matched, auto-escalate the alert to the specified role/user
4. Create an audit log entry for the automatic escalation

## Affected Files
- `alerts/signals.py` (needs to be created)
- `alerts/apps.py` (needs signal registration)
- `wazuh_integration/services.py:176` (where alerts are created)

## Suggested Fix
Create `alerts/signals.py`:
```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Alert
from settings_manager.models import EscalationRule

@receiver(post_save, sender=Alert)
def auto_escalate_alert(sender, instance, created, **kwargs):
    if not created:
        return
    rules = EscalationRule.objects.filter(is_active=True)
    for rule in rules:
        if rule.severity_condition and instance.severity != rule.severity_condition:
            continue
        if rule.alert_name_keyword and rule.alert_name_keyword.lower() not in instance.alert_name.lower():
            continue
        if rule.wazuh_rule_id and instance.rule_id != rule.wazuh_rule_id:
            continue
        # Match found - escalate
        instance.status = 'Escalated'
        instance.is_escalated = True
        instance.escalated_at = timezone.now()
        instance.save()
        break  # Only apply first matching rule
```

## QA Verification
1. Create an escalation rule: severity=Critical, escalate_to_role=SOC_ENG.
2. Seed/import a Critical alert → it must be auto-escalated.
3. Verify audit log shows the automatic escalation.
