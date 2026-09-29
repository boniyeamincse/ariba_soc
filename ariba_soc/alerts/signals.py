from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Alert
from settings_manager.models import EscalationRule

# Which SOC tier an EscalationRule.escalate_to_role lands an alert on.
# L1 has nowhere to route to from here (L1 is the triage starting point).
ROLE_TO_STATUS = {
    'L2': 'Escalated to L2',
    'SOC_ENG': 'Escalated to IR/IT',
    'SOC_MGR': 'Escalated to Management',
    'ADMIN': 'Escalated to Management',
}


def evaluate_auto_escalation(alert):
    """Check alert against active EscalationRules and escalate it if one
    matches. Safe to call on any alert regardless of how it was created
    (bulk_create doesn't fire post_save, so the sync pipeline calls this
    directly instead of relying on the signal below)."""
    if alert.status != 'New':
        return False
    for rule in EscalationRule.objects.filter(is_active=True):
        if rule.severity_condition and alert.severity != rule.severity_condition:
            continue
        if rule.alert_name_keyword and rule.alert_name_keyword.lower() not in alert.alert_name.lower():
            continue
        if rule.wazuh_rule_id and alert.rule_id != rule.wazuh_rule_id:
            continue
        target_status = ROLE_TO_STATUS.get(rule.escalate_to_role, 'Escalated to L2')
        alert.status = target_status
        alert.is_escalated = True
        alert.escalated_at = timezone.now()
        alert.save(update_fields=['status', 'is_escalated', 'escalated_at'])
        from .services import create_audit_log, _notify_escalation
        reason = f'{target_status} — auto-escalated by rule: {rule.rule_name}'
        create_audit_log(alert, None, 'Escalated', 'New', reason)
        _notify_escalation(alert, reason)
        return True
    return False


@receiver(post_save, sender=Alert)
def auto_escalate_alert(sender, instance, created, **kwargs):
    if created:
        evaluate_auto_escalation(instance)


@receiver(post_save, sender=Alert)
def trigger_alarm_notification(sender, instance, created, **kwargs):
    if created:
        from .services import emit_alarm_notification
        emit_alarm_notification(instance)
