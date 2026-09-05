from django.db import transaction
from django.utils import timezone
from .models import Incident, IncidentTimeline

ALLOWED_TRANSITIONS = {
    'NEW': ['CONFIRMED', 'CLOSED'],
    'CONFIRMED': ['INVESTIGATING', 'CLOSED'],
    'INVESTIGATING': ['CONTAINMENT', 'RESOLVED'],
    'CONTAINMENT': ['ERADICATION', 'INVESTIGATING'],
    'ERADICATION': ['RECOVERY', 'CONTAINMENT'],
    'RECOVERY': ['MONITORING', 'ERADICATION'],
    'MONITORING': ['RESOLVED', 'RECOVERY'],
    'RESOLVED': ['CLOSED', 'REOPENED'],
    'CLOSED': ['REOPENED'],
    'REOPENED': ['INVESTIGATING'],
}


class IncidentWorkflowError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def _create_timeline(incident, event_type, actor, title, description='', from_value='', to_value='', metadata=None, request_id=''):
    IncidentTimeline.objects.create(
        incident=incident,
        event_type=event_type,
        actor=actor,
        actor_role=getattr(actor, 'analyst_profile', None) and actor.analyst_profile.role or '',
        title=title,
        description=description,
        from_value=from_value,
        to_value=to_value,
        metadata=metadata or {},
        request_id=request_id,
    )


def confirm_incident(incident, user, version, request_id=''):
    with transaction.atomic():
        inc = Incident.objects.select_for_update().get(pk=incident.pk)
        if inc.version != version:
            raise IncidentWorkflowError('Incident has been modified. Please refresh.', 409)
        if inc.status != 'NEW':
            raise IncidentWorkflowError(f'Cannot confirm from {inc.status}', 400)
        old_status = inc.status
        inc.status = 'CONFIRMED'
        inc.version += 1
        inc.declared_at = inc.declared_at or timezone.now()
        inc.save(update_fields=['status', 'version', 'declared_at', 'updated_at'])
        _create_timeline(inc, 'STATUS_CHANGED', user, 'Incident confirmed', from_value=old_status, to_value='CONFIRMED', request_id=request_id)
    return inc


def start_investigation(incident, user, version, request_id=''):
    with transaction.atomic():
        inc = Incident.objects.select_for_update().get(pk=incident.pk)
        if inc.version != version:
            raise IncidentWorkflowError('Incident has been modified. Please refresh.', 409)
        if inc.status != 'CONFIRMED':
            raise IncidentWorkflowError(f'Cannot investigate from {inc.status}', 400)
        old_status = inc.status
        inc.status = 'INVESTIGATING'
        inc.version += 1
        inc.save(update_fields=['status', 'version', 'updated_at'])
        _create_timeline(inc, 'STATUS_CHANGED', user, 'Investigation started', from_value=old_status, to_value='INVESTIGATING', request_id=request_id)
    return inc


def start_containment(incident, user, version, evidence='', request_id=''):
    if not evidence:
        raise IncidentWorkflowError('Containment evidence is required', 400)
    with transaction.atomic():
        inc = Incident.objects.select_for_update().get(pk=incident.pk)
        if inc.version != version:
            raise IncidentWorkflowError('Incident has been modified. Please refresh.', 409)
        if inc.status not in ('INVESTIGATING', 'ERADICATION'):
            raise IncidentWorkflowError(f'Cannot start containment from {inc.status}', 400)
        old_status = inc.status
        inc.status = 'CONTAINMENT'
        inc.contained_at = timezone.now()
        inc.version += 1
        inc.save(update_fields=['status', 'contained_at', 'version', 'updated_at'])
        _create_timeline(inc, 'CONTAINED', user, 'Containment started', description=evidence, from_value=old_status, to_value='CONTAINMENT', request_id=request_id)
    return inc


def mark_eradicated(incident, user, version, evidence='', request_id=''):
    if not evidence:
        raise IncidentWorkflowError('Eradication evidence is required', 400)
    with transaction.atomic():
        inc = Incident.objects.select_for_update().get(pk=incident.pk)
        if inc.version != version:
            raise IncidentWorkflowError('Incident has been modified. Please refresh.', 409)
        if inc.status not in ('CONTAINMENT', 'RECOVERY'):
            raise IncidentWorkflowError(f'Cannot mark eradicated from {inc.status}', 400)
        old_status = inc.status
        inc.status = 'ERADICATION'
        inc.eradicated_at = timezone.now()
        inc.version += 1
        inc.save(update_fields=['status', 'eradicated_at', 'version', 'updated_at'])
        _create_timeline(inc, 'ERADICATED', user, 'Eradication completed', description=evidence, from_value=old_status, to_value='ERADICATION', request_id=request_id)
    return inc


def start_recovery(incident, user, version, evidence='', request_id=''):
    if not evidence:
        raise IncidentWorkflowError('Recovery evidence is required', 400)
    with transaction.atomic():
        inc = Incident.objects.select_for_update().get(pk=incident.pk)
        if inc.version != version:
            raise IncidentWorkflowError('Incident has been modified. Please refresh.', 409)
        if inc.status not in ('ERADICATION', 'MONITORING'):
            raise IncidentWorkflowError(f'Cannot start recovery from {inc.status}', 400)
        old_status = inc.status
        inc.status = 'RECOVERY'
        inc.recovered_at = timezone.now()
        inc.version += 1
        inc.save(update_fields=['status', 'recovered_at', 'version', 'updated_at'])
        _create_timeline(inc, 'RECOVERED', user, 'Recovery started', description=evidence, from_value=old_status, to_value='RECOVERY', request_id=request_id)
    return inc


def start_monitoring(incident, user, version, request_id=''):
    with transaction.atomic():
        inc = Incident.objects.select_for_update().get(pk=incident.pk)
        if inc.version != version:
            raise IncidentWorkflowError('Incident has been modified. Please refresh.', 409)
        if inc.status != 'RECOVERY':
            raise IncidentWorkflowError(f'Cannot start monitoring from {inc.status}', 400)
        old_status = inc.status
        inc.status = 'MONITORING'
        inc.version += 1
        inc.save(update_fields=['status', 'version', 'updated_at'])
        _create_timeline(inc, 'STATUS_CHANGED', user, 'Monitoring started', from_value=old_status, to_value='MONITORING', request_id=request_id)
    return inc


def resolve_incident(incident, user, version, resolution_summary='', request_id=''):
    if not resolution_summary:
        raise IncidentWorkflowError('Resolution summary is required', 400)
    with transaction.atomic():
        inc = Incident.objects.select_for_update().get(pk=incident.pk)
        if inc.version != version:
            raise IncidentWorkflowError('Incident has been modified. Please refresh.', 409)
        if inc.status not in ('INVESTIGATING', 'MONITORING'):
            raise IncidentWorkflowError(f'Cannot resolve from {inc.status}', 400)
        old_status = inc.status
        inc.status = 'RESOLVED'
        inc.resolved_at = timezone.now()
        inc.version += 1
        inc.save(update_fields=['status', 'resolved_at', 'version', 'updated_at'])
        _create_timeline(inc, 'RESOLVED', user, 'Incident resolved', description=resolution_summary, from_value=old_status, to_value='RESOLVED', request_id=request_id)
    return inc


def close_incident(incident, user, version, closure_reason='', request_id=''):
    if not closure_reason:
        raise IncidentWorkflowError('Closure reason is required', 400)
    with transaction.atomic():
        inc = Incident.objects.select_for_update().get(pk=incident.pk)
        if inc.version != version:
            raise IncidentWorkflowError('Incident has been modified. Please refresh.', 409)
        if inc.status != 'RESOLVED':
            raise IncidentWorkflowError(f'Cannot close from {inc.status}', 400)
        if not inc.linked_alerts.exists():
            raise IncidentWorkflowError('Cannot close incident without linked alerts', 400)
        old_status = inc.status
        inc.status = 'CLOSED'
        inc.closed_at = timezone.now()
        inc.version += 1
        inc.save(update_fields=['status', 'closed_at', 'version', 'updated_at'])
        _create_timeline(inc, 'CLOSED', user, 'Incident closed', description=closure_reason, from_value=old_status, to_value='CLOSED', request_id=request_id)
    return inc


def reopen_incident(incident, user, version, reason='', request_id=''):
    if not reason:
        raise IncidentWorkflowError('Reopen reason is required', 400)
    with transaction.atomic():
        inc = Incident.objects.select_for_update().get(pk=incident.pk)
        if inc.version != version:
            raise IncidentWorkflowError('Incident has been modified. Please refresh.', 409)
        if inc.status not in ('RESOLVED', 'CLOSED'):
            raise IncidentWorkflowError(f'Cannot reopen from {inc.status}', 400)
        old_status = inc.status
        inc.status = 'REOPENED'
        inc.closed_at = None
        inc.resolved_at = None
        inc.version += 1
        inc.save(update_fields=['status', 'closed_at', 'resolved_at', 'version', 'updated_at'])
        _create_timeline(inc, 'REOPENED', user, 'Incident reopened', description=reason, from_value=old_status, to_value='REOPENED', request_id=request_id)
    return inc
