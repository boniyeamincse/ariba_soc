from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Alert
from settings_manager.models import EscalationRule


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
        alert.status = 'Escalated'
        alert.is_escalated = True
        alert.escalated_at = timezone.now()
        alert.save(update_fields=['status', 'is_escalated', 'escalated_at'])
        from .services import create_audit_log, _notify_escalation
        create_audit_log(alert, None, 'Escalated', 'New', f'Auto-escalated by rule: {rule.rule_name}')
        _notify_escalation(alert, f'Auto-escalated by rule: {rule.rule_name}')
        return True
    return False


@receiver(post_save, sender=Alert)
def auto_escalate_alert(sender, instance, created, **kwargs):
    if created:
        evaluate_auto_escalation(instance)
