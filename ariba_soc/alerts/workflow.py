import uuid
import logging
from django.db import transaction
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils import timezone

from .models import (
    Alert, AlertEscalation, AlertTransition, AlertComment, AlertAuditLog, Notification,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowed transitions: from_state -> set of valid to_states
# ---------------------------------------------------------------------------
ALLOWED_TRANSITIONS = {
    'NEW':                    {'QUEUED_L1'},
    'QUEUED_L1':              {'IN_PROGRESS_L1', 'CLOSED', 'ARCHIVED'},
    'IN_PROGRESS_L1':         {'QUEUED_L1', 'PENDING_L2_ACCEPTANCE', 'RETURNED_TO_L1', 'RESOLVED', 'CLOSED', 'ARCHIVED'},
    'PENDING_L2_ACCEPTANCE':  {'IN_PROGRESS_L2', 'RETURNED_TO_L1', 'CANCELLED'},
    'IN_PROGRESS_L2':         {'PENDING_L3_ACCEPTANCE', 'RETURNED_TO_L2', 'RETURNED_TO_L1', 'RESOLVED', 'CLOSED', 'ARCHIVED'},
    'RETURNED_TO_L1':         {'IN_PROGRESS_L1', 'PENDING_L2_ACCEPTANCE', 'RESOLVED', 'CLOSED', 'ARCHIVED'},
    'PENDING_L3_ACCEPTANCE':  {'IN_PROGRESS_L3', 'RETURNED_TO_L2', 'CANCELLED'},
    'IN_PROGRESS_L3':         {'RETURNED_TO_L2', 'INCIDENT', 'RESOLVED', 'CLOSED', 'ARCHIVED'},
    'RETURNED_TO_L2':         {'IN_PROGRESS_L2', 'PENDING_L3_ACCEPTANCE', 'RESOLVED', 'CLOSED', 'ARCHIVED'},
    'INCIDENT':               {'RESOLVED', 'CLOSED', 'ARCHIVED'},
    'RESOLVED':               {'CLOSED', 'REOPENED'},
    'CLOSED':                 {'REOPENED', 'QUEUED_L1', 'ARCHIVED'},
    'REOPENED':               {'QUEUED_L1', 'NEW'},
    'ARCHIVED':               {'REOPENED'},
}

# Which tiers are allowed to perform which actions
TIER_ACTIONS = {
    'claim':        {'L1', 'L2', 'L3', 'SOC_MGR', 'ADMIN'},
    'escalate':     {'L1', 'L2', 'L3', 'SOC_MGR', 'ADMIN'},
    'accept':       {'L2', 'L3', 'SOC_MGR', 'ADMIN'},
    'return':       {'L2', 'L3', 'SOC_MGR', 'ADMIN'},
    'resolve':      {'L1', 'L2', 'L3', 'SOC_MGR', 'ADMIN'},
    'close':        {'L1', 'L2', 'L3', 'SOC_MGR', 'ADMIN'},
    'reopen':       {'L1', 'L2', 'L3', 'SOC_MGR', 'ADMIN'},
    'create_incident': {'L3', 'SOC_MGR', 'ADMIN'},
}

# Escalation direction rules
ESCALATION_PATH = {
    'L1': 'L2',
    'L2': 'L3',
}

# States from which the SLA-breach worker may auto-escalate an alert one tier
# up. This is intentionally more permissive than ALLOWED_TRANSITIONS because a
# system action should be able to escalate a breached alert that was never
# claimed (NEW/QUEUED_L1) as well as one already in progress.
SYSTEM_ESCALATION_SOURCE_STATES = {
    'NEW', 'QUEUED_L1', 'IN_PROGRESS_L1', 'RETURNED_TO_L1',
    'IN_PROGRESS_L2', 'RETURNED_TO_L2',
}


class WorkflowError(Exception):
    """Raised when a workflow transition is invalid."""
    def __init__(self, message, status_code=400):
        self.status_code = status_code
        super().__init__(message)


def _get_user_role(user):
    profile = getattr(user, 'analyst_profile', None)
    if not profile:
        return None
    return profile.role


def _check_active(user):
    profile = getattr(user, 'analyst_profile', None)
    if not profile or not profile.is_active:
        raise WorkflowError('Your account is inactive.', 403)


def _check_action_perm(user, action):
    role = _get_user_role(user)
    if not role:
        raise WorkflowError('No role assigned.', 403)
    allowed = TIER_ACTIONS.get(action, set())
    if role not in allowed:
        raise WorkflowError(f'Role {role} is not authorized to {action}.', 403)


def _create_transition(alert, from_state, to_state, action, actor, reason='', metadata=None, request=None):
    request_id = ''
    if request:
        request_id = request.headers.get('X-Request-ID', '') or str(uuid.uuid4())[:16]
    AlertTransition.objects.create(
        alert=alert,
        from_state=from_state,
        to_state=to_state,
        action=action,
        actor=actor,
        actor_role=_get_user_role(actor) or '',
        reason=reason,
        metadata=metadata or {},
        request_id=request_id,
    )


def _create_audit_log(alert, user, action, old_value='', new_value='', request=None):
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


def _send_notification(user, message, link=''):
    try:
        Notification.objects.create(user=user, message=message, link=link)
    except Exception:
        logger.exception('Failed to create notification for user %s', user.username)


def _notify_tier_users(tier, message, link='', exclude_user=None):
    from accounts.models import AnalystProfile
    profile_users = User.objects.filter(
        analyst_profile__role=tier,
        is_active=True,
        analyst_profile__is_active=True,
    )
    if exclude_user:
        profile_users = profile_users.exclude(id=exclude_user.id)
    for u in profile_users:
        _send_notification(u, message, link)


def _validate_transition(alert, to_state):
    current = alert.workflow_state
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if to_state not in allowed:
        raise WorkflowError(
            f'Cannot transition from {current} to {to_state}.',
            status_code=409,
        )


def _check_version(alert, expected_version):
    if alert.workflow_version != expected_version:
        raise WorkflowError(
            f'Stale data: expected version {expected_version}, got {alert.workflow_version}. '
            'Please refresh and try again.',
            status_code=409,
        )


def _set_workflow_state(alert, new_state, request=None):
    old_state = alert.workflow_state
    alert.workflow_state = new_state
    alert.workflow_version += 1
    alert.status_updated_at = timezone.now()
    alert.save()
    _create_transition(alert, old_state, new_state, f'transition_to_{new_state}', alert.assignee or None, request=request)


def _derive_legacy_status(workflow_state):
    mapping = {
        'NEW': 'New',
        'QUEUED_L1': 'New',
        'IN_PROGRESS_L1': 'In Progress',
        'PENDING_L2_ACCEPTANCE': 'Escalated to L2',
        'IN_PROGRESS_L2': 'In Progress',
        'RETURNED_TO_L1': 'In Progress',
        'PENDING_L3_ACCEPTANCE': 'Escalated to L3',
        'IN_PROGRESS_L3': 'In Progress',
        'RETURNED_TO_L2': 'In Progress',
        'INCIDENT': 'In Progress',
        'RESOLVED': 'Closed',
        'CLOSED': 'Closed',
        'REOPENED': 'New',
        'ARCHIVED': 'Archived',
    }
    return mapping.get(workflow_state, 'New')


# ---------------------------------------------------------------------------
# Public workflow actions
# ---------------------------------------------------------------------------

def claim_alert(alert_id, actor, expected_version, request=None):
    alert = _acquire_lock(alert_id)
    _check_active(actor)
    _check_action_perm(actor, 'claim')
    _check_version(alert, expected_version)
    _validate_transition(alert, 'IN_PROGRESS_L1')
    old_state = alert.workflow_state
    with transaction.atomic():
        alert.assignee = actor
        alert.assigned_by = actor
        alert.assigned_at = timezone.now()
        alert.acknowledged_at = alert.acknowledged_at or timezone.now()
        alert.current_tier = 'L1'
        alert.current_owner_team = 'L1'
        alert.workflow_state = 'IN_PROGRESS_L1'
        alert.workflow_version += 1
        alert.status_updated_at = timezone.now()
        alert.save()
        _create_transition(alert, old_state, 'IN_PROGRESS_L1', 'claim', actor,
                           request=request)
        _create_audit_log(alert, actor, 'Assigned', old_state, 'IN_PROGRESS_L1', request)
    return alert


def escalate_alert(alert_id, actor, target_tier, reason, expected_version, request=None):
    _check_active(actor)
    _check_action_perm(actor, 'escalate')
    if not reason:
        raise WorkflowError('Escalation reason is required.', 400)
    target_tier = target_tier.upper()
    if target_tier not in ('L2', 'L3'):
        raise WorkflowError('Invalid target tier. Only L2 and L3 are valid targets.', 400)
    role = _get_user_role(actor)
    if role in ESCALATION_PATH:
        allowed_target = ESCALATION_PATH[role]
        if target_tier != allowed_target:
            raise WorkflowError(
                f'{role} can only escalate to {allowed_target}, not {target_tier}.',
                status_code=403,
            )

    alert = _acquire_lock(alert_id)
    _check_version(alert, expected_version)

    source_tier = alert.current_tier or 'L1'
    workflow_target_state = f'PENDING_{target_tier}_ACCEPTANCE'
    _validate_transition(alert, workflow_target_state)

    with transaction.atomic():
        escalation = AlertEscalation.objects.create(
            alert=alert,
            source_tier=source_tier,
            target_tier=target_tier,
            escalated_by=actor,
            escalation_reason=reason,
            escalation_status='PENDING',
            escalated_at=timezone.now(),
        )
        alert.current_tier = target_tier
        alert.current_owner_team = target_tier
        alert.escalated_from_tier = source_tier
        alert.escalated_to_tier = target_tier
        alert.escalation_status = 'pending_acceptance'
        alert.escalation_reason = reason
        alert.escalated_at = alert.escalated_at or timezone.now()
        alert.is_escalated = True
        alert.workflow_state = workflow_target_state
        alert.workflow_version += 1
        alert.status_updated_at = timezone.now()
        alert.save()

        AlertComment.objects.create(
            alert=alert, user=actor,
            comment=f'Escalated from {source_tier} to {target_tier}: {reason}',
            comment_type='Escalation Note',
        )
        _create_transition(alert, alert.workflow_state, workflow_target_state, 'escalate',
                           actor, reason=reason,
                           metadata={'escalation_id': escalation.id, 'target_tier': target_tier},
                           request=request)
        _create_audit_log(alert, actor, 'Escalated',
                          f'{source_tier} → {target_tier}', reason, request)

        from django.urls import reverse
        link = reverse('alerts:detail', args=[alert.id])
        msg = f"Alert '{alert.alert_name}' escalated from {source_tier} to {target_tier}. Reason: {reason}"
        _notify_tier_users(target_tier, msg, link=link, exclude_user=actor)

    return alert


def accept_escalation(alert_id, actor, expected_version, request=None):
    _check_active(actor)
    _check_action_perm(actor, 'accept')
    alert = _acquire_lock(alert_id)
    _check_version(alert, expected_version)
    _validate_transition(alert, 'IN_PROGRESS_L2')

    target_tier = alert.current_tier
    user_role = _get_user_role(actor)
    from accounts.decorators import TIER_ORDER
    if TIER_ORDER.get(user_role, 0) < TIER_ORDER.get(target_tier, 0) and user_role not in ('SOC_MGR', 'ADMIN'):
        raise WorkflowError(f'Cannot accept alerts escalated to {target_tier}.', 403)

    with transaction.atomic():
        escalation = AlertEscalation.objects.filter(
            alert=alert, escalation_status='PENDING', target_tier=target_tier,
        ).select_for_update().first()
        if not escalation:
            raise WorkflowError('No pending escalation found for this tier.', 409)

        escalation.escalation_status = 'ACCEPTED'
        escalation.accepted_by = actor
        escalation.accepted_at = timezone.now()
        escalation.save()

        alert.assignee = actor
        alert.accepted_by = actor
        alert.accepted_at = timezone.now()
        alert.escalation_status = 'accepted'
        alert.workflow_state = f'IN_PROGRESS_{target_tier}'
        alert.workflow_version += 1
        alert.status_updated_at = timezone.now()
        alert.save()

        AlertComment.objects.create(
            alert=alert, user=actor,
            comment=f'Accepted escalation to {target_tier} by {actor.username}',
            comment_type='Analyst Note',
        )
        old_state = f'PENDING_{target_tier}_ACCEPTANCE'
        _create_transition(alert, old_state, f'IN_PROGRESS_{target_tier}', 'accept',
                           actor, request=request)
        _create_audit_log(alert, actor, 'Status Changed', old_state, f'IN_PROGRESS_{target_tier}', request)

        from django.urls import reverse
        link = reverse('alerts:detail', args=[alert.id])
        _notify_tier_users(target_tier, f"Alert '{alert.alert_name}' accepted by {actor.username}.", link=link)

    return alert


def return_escalation(alert_id, actor, reason, expected_version, request=None):
    _check_active(actor)
    _check_action_perm(actor, 'return')
    if not reason:
        raise WorkflowError('Return reason is required.', 400)
    alert = _acquire_lock(alert_id)
    _check_version(alert, expected_version)

    target_tier = alert.current_tier
    source_tier = alert.escalated_from_tier
    if not source_tier:
        latest_esc = AlertEscalation.objects.filter(
            alert=alert, target_tier=target_tier,
        ).order_by('-escalated_at').first()
        source_tier = latest_esc.source_tier if latest_esc else 'L1'
    workflow_source_state = f'RETURNED_TO_{source_tier}'
    _validate_transition(alert, workflow_source_state)

    with transaction.atomic():
        escalation = AlertEscalation.objects.filter(
            alert=alert, escalation_status='ACCEPTED', target_tier=target_tier,
        ).select_for_update().first()
        if not escalation:
            raise WorkflowError('No accepted escalation found for this tier.', 409)

        escalation.escalation_status = 'RETURNED'
        escalation.returned_by = actor
        escalation.returned_at = timezone.now()
        escalation.return_reason = reason
        escalation.save()

        alert.current_tier = source_tier
        alert.current_owner_team = source_tier
        alert.escalation_status = 'returned'
        alert.returned_by = actor
        alert.returned_at = timezone.now()
        alert.return_reason = reason
        alert.workflow_state = workflow_source_state
        alert.workflow_version += 1
        alert.status_updated_at = timezone.now()
        alert.save()

        AlertComment.objects.create(
            alert=alert, user=actor,
            comment=f'Returned from {target_tier} to {source_tier}: {reason}',
            comment_type='Escalation Note',
        )
        _create_transition(alert, f'IN_PROGRESS_{target_tier}', workflow_source_state, 'return',
                           actor, reason=reason, request=request)
        _create_audit_log(alert, actor, 'Status Changed', f'IN_PROGRESS_{target_tier}',
                          workflow_source_state, request)

        from django.urls import reverse
        link = reverse('alerts:detail', args=[alert.id])
        msg = f"Alert '{alert.alert_name}' returned from {target_tier} to {source_tier}. Reason: {reason}"
        _notify_tier_users(source_tier, msg, link=link, exclude_user=actor)

    return alert


def resolve_alert(alert_id, actor, resolution, expected_version, request=None):
    _check_active(actor)
    _check_action_perm(actor, 'resolve')
    alert = _acquire_lock(alert_id)
    _check_version(alert, expected_version)

    _validate_transition(alert, 'RESOLVED')

    with transaction.atomic():
        alert.verdict = resolution or alert.verdict
        alert.closure_reason = alert.closure_reason or resolution
        alert.resolved_at = timezone.now()
        alert.workflow_state = 'RESOLVED'
        alert.workflow_version += 1
        alert.status_updated_at = timezone.now()
        alert.save()

        AlertComment.objects.create(
            alert=alert, user=actor,
            comment=f'Resolved: {resolution}',
            comment_type='Closure Note',
        )
        _create_transition(alert, alert.workflow_state, 'RESOLVED', 'resolve',
                           actor, reason=resolution, request=request)
        _create_audit_log(alert, actor, 'Status Changed', alert.workflow_state, 'RESOLVED', request)

    return alert


def close_alert(alert_id, actor, verdict, closure_reason, expected_version, request=None):
    _check_active(actor)
    _check_action_perm(actor, 'close')
    alert = _acquire_lock(alert_id)
    _check_version(alert, expected_version)

    _validate_transition(alert, 'CLOSED')

    with transaction.atomic():
        alert.verdict = verdict or alert.verdict
        alert.closure_reason = closure_reason or alert.closure_reason
        alert.closed_at = timezone.now()
        alert.workflow_state = 'CLOSED'
        alert.workflow_version += 1
        alert.status_updated_at = timezone.now()
        alert.save()

        AlertComment.objects.create(
            alert=alert, user=actor,
            comment=f'Closed with verdict {verdict}: {closure_reason}',
            comment_type='Closure Note',
        )
        _create_transition(alert, alert.workflow_state, 'CLOSED', 'close',
                           actor, reason=closure_reason, request=request)
        _create_audit_log(alert, actor, 'Closed', alert.workflow_state, verdict, request)

    return alert


def reopen_alert(alert_id, actor, reason, expected_version, request=None):
    _check_active(actor)
    _check_action_perm(actor, 'reopen')
    alert = _acquire_lock(alert_id)
    _check_version(alert, expected_version)

    _validate_transition(alert, 'QUEUED_L1')

    with transaction.atomic():
        alert.closed_at = None
        alert.resolved_at = None
        alert.closure_reason = ''
        alert.current_tier = 'L1'
        alert.current_owner_team = 'L1'
        alert.assignee = None
        alert.escalation_status = ''
        alert.escalated_from_tier = ''
        alert.escalated_to_tier = ''
        alert.workflow_state = 'QUEUED_L1'
        alert.workflow_version += 1
        alert.status_updated_at = timezone.now()
        alert.save()

        AlertComment.objects.create(
            alert=alert, user=actor,
            comment=f'Reopened: {reason}',
            comment_type='Analyst Note',
        )
        old_state = alert.workflow_state
        _create_transition(alert, old_state, 'QUEUED_L1', 'reopen',
                           actor, reason=reason, request=request)
        _create_audit_log(alert, actor, 'Reopened', old_state, 'QUEUED_L1', request)

    return alert


def create_incident(alert_id, actor, reason, expected_version, request=None):
    _check_active(actor)
    _check_action_perm(actor, 'create_incident')
    alert = _acquire_lock(alert_id)
    _check_version(alert, expected_version)

    _validate_transition(alert, 'INCIDENT')

    with transaction.atomic():
        alert.is_incident_candidate = True
        alert.workflow_state = 'INCIDENT'
        alert.workflow_version += 1
        alert.status_updated_at = timezone.now()
        alert.save()

        AlertComment.objects.create(
            alert=alert, user=actor,
            comment=f'Incident created: {reason}',
            comment_type='Manager Note',
        )
        _create_transition(alert, alert.workflow_state, 'INCIDENT', 'create_incident',
                           actor, reason=reason, request=request)
        _create_audit_log(alert, actor, 'Escalated', alert.workflow_state, 'INCIDENT', request)

        from django.urls import reverse
        link = reverse('alerts:detail', args=[alert.id])
        msg = f"Incident created for alert '{alert.alert_name}' by {actor.username}. Reason: {reason}"
        _notify_tier_users('SOC_MGR', msg, link=link)

    return alert


def _acquire_lock(alert_id):
    try:
        return Alert.objects.select_for_update().get(id=alert_id)
    except Alert.DoesNotExist:
        raise WorkflowError('Alert not found.', 404)


def system_auto_escalate(alert, reason='SLA breach auto-escalation', request=None):
    """Auto-escalate an alert one tier up as a *system* action.

    Unlike ``escalate_alert`` this bypasses actor role checks (there is no human
    actor) and is safe to call from the SLA-breach worker. Returns the alert on
    success, or ``None`` when the alert cannot be escalated (already at L3, or
    the workflow state does not permit an escalation transition).
    """
    source_tier = alert.current_tier or 'L1'
    target = ESCALATION_PATH.get(source_tier)
    if target not in ('L2', 'L3'):
        return None
    workflow_target_state = f'PENDING_{target}_ACCEPTANCE'
    if alert.workflow_state not in SYSTEM_ESCALATION_SOURCE_STATES:
        return None

    with transaction.atomic():
        old_state = alert.workflow_state
        AlertEscalation.objects.create(
            alert=alert,
            source_tier=source_tier,
            target_tier=target,
            escalated_by=None,
            escalation_reason=reason,
            escalation_status='PENDING',
            escalated_at=timezone.now(),
        )
        alert.current_tier = target
        alert.current_owner_team = target
        alert.escalated_from_tier = source_tier
        alert.escalated_to_tier = target
        alert.escalation_status = 'pending_acceptance'
        alert.escalation_reason = reason
        alert.escalated_at = alert.escalated_at or timezone.now()
        alert.is_escalated = True
        alert.workflow_state = workflow_target_state
        alert.workflow_version += 1
        alert.status_updated_at = timezone.now()
        alert.save()

        AlertComment.objects.create(
            alert=alert, user=None,
            comment=f'Auto-escalated {source_tier} → {target} (system): {reason}',
            comment_type='Escalation Note',
        )
        _create_transition(alert, old_state, workflow_target_state, 'auto_escalate',
                           None, reason=reason, request=request)
        _create_audit_log(alert, None, 'Escalated', f'{source_tier} → {target}', reason, request)

        from django.urls import reverse
        link = reverse('alerts:detail', args=[alert.id])
        msg = f"Alert '{alert.alert_name}' auto-escalated from {source_tier} to {target} due to SLA breach."
        _notify_tier_users(target, msg, link=link)

    return alert
