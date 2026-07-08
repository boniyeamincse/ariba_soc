from django.utils import timezone
from django.contrib.auth.models import User
from .models import Alert, AlertComment, AlertAuditLog

def create_audit_log(alert, user, action, old_value='', new_value='', request=None):
    ip = ''
    ua = ''
    if request:
        ip = request.META.get('REMOTE_ADDR', '')
        ua = request.META.get('HTTP_USER_AGENT', '')
    AlertAuditLog.objects.create(
        alert=alert,
        user=user,
        action=action,
        old_value=str(old_value),
        new_value=str(new_value),
        ip_address=ip,
        user_agent=ua,
    )


def update_alert(alert, form, user, request=None):
    changed = []
    for field in ['assignee', 'status', 'severity', 'verdict', 'priority']:
        old = str(getattr(alert, field) or '')
        new = str(form.cleaned_data.get(field) or '')
        if old != new:
            setattr(alert, field, form.cleaned_data[field])
            if field == 'status' and form.cleaned_data[field] == 'In Progress':
                alert.acknowledged_at = timezone.now()
            if field == 'status' and form.cleaned_data[field] == 'Escalated':
                alert.is_escalated = True
                alert.escalated_at = timezone.now()
            action_map = {
                'assignee': 'Assigned',
                'status': 'Status Changed',
                'severity': 'Severity Changed',
                'verdict': 'Verdict Changed',
                'priority': 'Priority Changed',
            }
            create_audit_log(alert, user, action_map.get(field, 'Updated'), old, new, request)
            changed.append(field)

    comment_text = form.cleaned_data.get('analyst_comment')
    if comment_text:
        AlertComment.objects.create(
            alert=alert,
            user=user,
            comment=comment_text,
            comment_type='Analyst Note'
        )
        alert.analyst_comment = comment_text
        create_audit_log(alert, user, 'Comment Added', '', comment_text[:200], request)

    escalation = form.cleaned_data.get('escalation_reason')
    if escalation:
        alert.escalation_reason = escalation
        AlertComment.objects.create(
            alert=alert,
            user=user,
            comment=f"Escalation reason: {escalation}",
            comment_type='Escalation Note'
        )

    remediation = form.cleaned_data.get('remediation_note')
    if remediation:
        alert.remediation_note = remediation
        AlertComment.objects.create(
            alert=alert,
            user=user,
            comment=f"Remediation: {remediation}",
            comment_type='Remediation Note'
        )

    closure = form.cleaned_data.get('closure_reason')
    if closure:
        alert.closure_reason = closure
        AlertComment.objects.create(
            alert=alert,
            user=user,
            comment=f"Closure reason: {closure}",
            comment_type='Closure Note'
        )

    if alert.status == 'Closed' and form.cleaned_data.get('verdict'):
        create_audit_log(alert, user, 'Closed', '', alert.verdict, request)

    alert.save()
    return changed


def assign_alert(alert, user, assignee=None, request=None):
    if assignee is None:
        assignee = user
    old = str(alert.assignee)
    alert.assignee = assignee
    alert.assigned_by = user
    alert.assigned_at = timezone.now()
    if alert.status == 'New':
        alert.status = 'In Progress'
        alert.acknowledged_at = timezone.now()
    alert.save()
    create_audit_log(alert, user, 'Assigned', old, str(assignee), request)
