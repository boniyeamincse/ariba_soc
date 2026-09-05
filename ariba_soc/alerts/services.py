from django.utils import timezone
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from settings_manager.models import NotificationSetting
from .models import Alert, AlertComment, AlertAuditLog, Notification

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
            if field == 'status' and form.cleaned_data[field].startswith('Escalated'):
                alert.is_escalated = True
                alert.escalated_at = timezone.now()
                _notify_escalation(alert, f"{form.cleaned_data[field]} — {form.cleaned_data.get('escalation_reason', '')}")
            action_map = {
                'assignee': 'Assigned',
                'status': 'Status Changed',
                'severity': 'Severity Changed',
                'verdict': 'Verdict Changed',
                'priority': 'Priority Changed',
            }
            create_audit_log(alert, user, action_map.get(field, 'Updated'), old, new, request)
            changed.append(field)
            
            # Send notification if assignee changed and it's not the current user
            if field == 'assignee' and alert.assignee and alert.assignee != user:
                _notify_assignment(alert, alert.assignee, user, request)

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
    if form.cleaned_data.get('status') == 'Closed' and not closure:
        raise ValueError('Analyst comment (closure reason) is mandatory when closing an alert.')
    if closure:
        alert.closure_reason = closure
        AlertComment.objects.create(
            alert=alert,
            user=user,
            comment=f"Closure reason: {closure}",
            comment_type='Closure Note'
        )

    lessons_learned = form.cleaned_data.get('lessons_learned')
    if lessons_learned:
        alert.root_cause_summary = lessons_learned
        AlertComment.objects.create(
            alert=alert,
            user=user,
            comment=f"Lessons learned: {lessons_learned}",
            comment_type='Lessons Learned'
        )

    if alert.status == 'Closed' and form.cleaned_data.get('verdict'):
        create_audit_log(alert, user, 'Closed', '', alert.verdict, request)

    alert.save()
    return changed


def _notify_assignment(alert, assignee, assigner, request=None):
    """Helper to send in-app notification and email to the assignee."""
    try:
        # Create In-App Notification
        link = reverse('alerts:detail', args=[alert.id])
        msg = f"Alert '{alert.alert_name}' was assigned to you by {assigner.username}."
        Notification.objects.create(user=assignee, message=msg, link=link)
        
        # Send Email
        if assignee.email:
            subject = f"[Ariba SOC] Alert Assigned: {alert.alert_name}"
            body = f"Hello {assignee.username},\n\nAn alert has been assigned to you by {assigner.username}.\n\nAlert: {alert.alert_name}\nSeverity: {alert.severity}\n\nPlease check your dashboard for details.\n\nThank you,\nAriba SOC"
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [assignee.email], fail_silently=True)
    except Exception as e:
        pass


def _notify_escalation(alert, reason=''):
    """Notify whoever Notification Settings says should hear about an
    escalation. Best-effort: a notification failure must never block the
    escalation itself."""
    try:
        settings_rows = NotificationSetting.objects.filter(event_type='ALERT_ESCALATED', is_active=True)
        if not settings_rows.exists():
            return
        link = reverse('alerts:detail', args=[alert.id])
        msg = f"Alert '{alert.alert_name}' was escalated." + (f" Reason: {reason}" if reason else '')

        recipients = set()
        for setting in settings_rows:
            if setting.recipient_user_id:
                recipients.add(setting.recipient_user)
            elif setting.recipient_role:
                for u in User.objects.filter(is_active=True, analyst_profile__role=setting.recipient_role):
                    recipients.add(u)

        for user in recipients:
            Notification.objects.create(user=user, message=msg, link=link)
            if user.email:
                send_mail(
                    f'[Ariba SOC] Alert Escalated: {alert.alert_name}',
                    f'{msg}\n\nSeverity: {alert.severity}\n\nPlease check your dashboard for details.',
                    settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True,
                )
    except Exception:
        pass


def assign_alert(alert, user, assignee=None, request=None):
    if assignee is None:
        assignee = user
    old = str(alert.assignee)
    
    notify = False
    if alert.assignee != assignee and assignee != user:
        notify = True
        
    alert.assignee = assignee
    alert.assigned_by = user
    alert.assigned_at = timezone.now()
    if alert.status == 'New':
        alert.status = 'In Progress'
        alert.acknowledged_at = timezone.now()
    alert.save()
    create_audit_log(alert, user, 'Assigned', old, str(assignee), request)
    
    if notify:
        _notify_assignment(alert, assignee, user, request)

