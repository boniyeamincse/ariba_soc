from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Alert
from settings_manager.models import EscalationRule


@receiver(post_save, sender=Alert)
def auto_escalate_alert(sender, instance, created, **kwargs):
    if not created or instance.status != 'New':
        return
    rules = EscalationRule.objects.filter(is_active=True)
    for rule in rules:
        if rule.severity_condition and instance.severity != rule.severity_condition:
            continue
        if rule.alert_name_keyword and rule.alert_name_keyword.lower() not in instance.alert_name.lower():
            continue
        if rule.wazuh_rule_id and instance.rule_id != rule.wazuh_rule_id:
            continue
        instance.status = 'Escalated'
        instance.is_escalated = True
        instance.escalated_at = timezone.now()
        instance.save(update_fields=['status', 'is_escalated', 'escalated_at'])
        from .services import create_audit_log
        create_audit_log(instance, None, 'Escalated', 'New', f'Auto-escalated by rule: {rule.rule_name}')
        break
