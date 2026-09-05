from django.utils import timezone
from vulnerabilities.models import VulnerabilityCase, VulnerabilityAuditLog, ALLOWED_TRANSITIONS


class RemediationError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def assign_case(case, user, owner):
    if case.status not in ('NEW', 'REOPENED'):
        raise RemediationError('Only NEW or REOPENED vulnerabilities can be assigned')
    case.owner = owner
    case.status = 'ASSIGNED'
    case.save(update_fields=['owner', 'status', 'updated_at'])
    VulnerabilityAuditLog.objects.create(
        vulnerability=case, user=user, action='Assigned',
        old_value=case.owner.username if case.owner else '',
        new_value=owner.username,
    )
    return case


def start_progress(case, user):
    if case.status not in ('ASSIGNED', 'REOPENED'):
        raise RemediationError('Only ASSIGNED or REOPENED vulnerabilities can be started')
    case.status = 'IN_PROGRESS'
    case.save(update_fields=['status', 'updated_at'])
    VulnerabilityAuditLog.objects.create(
        vulnerability=case, user=user, action='Status Changed',
        old_value=case.status, new_value='IN_PROGRESS',
    )
    return case


def await_patch(case, user):
    if case.status != 'IN_PROGRESS':
        raise RemediationError('Only IN_PROGRESS vulnerabilities can await patch')
    case.status = 'AWAITING_PATCH'
    case.save(update_fields=['status', 'updated_at'])
    VulnerabilityAuditLog.objects.create(
        vulnerability=case, user=user, action='Status Changed',
        old_value='IN_PROGRESS', new_value='AWAITING_PATCH',
    )
    return case


def await_verification(case, user):
    if case.status not in ('IN_PROGRESS', 'AWAITING_PATCH'):
        raise RemediationError('Only IN_PROGRESS or AWAITING_PATCH can await verification')
    case.status = 'AWAITING_VERIFICATION'
    case.save(update_fields=['status', 'updated_at'])
    VulnerabilityAuditLog.objects.create(
        vulnerability=case, user=user, action='Status Changed',
        old_value=case.status, new_value='AWAITING_VERIFICATION',
    )
    return case


def resolve_case(case, user):
    if case.status not in ('IN_PROGRESS', 'AWAITING_VERIFICATION', 'AWAITING_PATCH'):
        raise RemediationError('Current status cannot be resolved')
    case.status = 'RESOLVED'
    case.verified_by = user
    case.verified_at = timezone.now()
    case.save(update_fields=['status', 'verified_by', 'verified_at', 'updated_at'])
    VulnerabilityAuditLog.objects.create(
        vulnerability=case, user=user, action='Resolved',
        old_value=case.status, new_value='RESOLVED',
    )
    return case


def accept_risk(case, user, reason):
    if case.status in ('RESOLVED', 'FALSE_POSITIVE'):
        raise RemediationError('Resolved or false-positive vulnerabilities cannot accept risk')
    case.risk_accepted = True
    case.risk_acceptance_reason = reason
    case.risk_accepted_by = user
    case.risk_accepted_at = timezone.now()
    case.status = 'RISK_ACCEPTED'
    case.save(update_fields=[
        'risk_accepted', 'risk_acceptance_reason', 'risk_accepted_by',
        'risk_accepted_at', 'status', 'updated_at',
    ])
    VulnerabilityAuditLog.objects.create(
        vulnerability=case, user=user, action='Risk Accepted',
        new_value=reason,
    )
    return case


def mark_false_positive(case, user, reason=''):
    if case.status in ('RESOLVED', 'RISK_ACCEPTED'):
        raise RemediationError('Resolved or risk-accepted vulnerabilities cannot be marked false positive')
    case.status = 'FALSE_POSITIVE'
    case.save(update_fields=['status', 'updated_at'])
    VulnerabilityAuditLog.objects.create(
        vulnerability=case, user=user, action='False Positive',
        note=reason,
    )
    return case


def reopen_case(case, user, reason=''):
    if case.status not in ('RESOLVED', 'RISK_ACCEPTED', 'FALSE_POSITIVE'):
        raise RemediationError('Only resolved, risk-accepted, or false-positive can be reopened')
    case.status = 'REOPENED'
    case.risk_accepted = False
    case.risk_acceptance_reason = ''
    case.verified_by = None
    case.verified_at = None
    case.save(update_fields=[
        'status', 'risk_accepted', 'risk_acceptance_reason',
        'verified_by', 'verified_at', 'updated_at',
    ])
    VulnerabilityAuditLog.objects.create(
        vulnerability=case, user=user, action='Reopened',
        note=reason,
    )
    return case


def add_note(case, user, note):
    case.remediation_note = note
    case.save(update_fields=['remediation_note', 'updated_at'])
    VulnerabilityAuditLog.objects.create(
        vulnerability=case, user=user, action='Note Added',
        note=note,
    )
    return case
