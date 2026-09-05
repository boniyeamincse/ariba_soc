from django.utils import timezone
from datetime import timedelta


PRIORITY_SLA_HOURS = {
    'CRITICAL': 24,
    'HIGH': 72,
    'MEDIUM': 168,
    'LOW': 720,
    'INFO': 2160,
}


def calculate_risk_score(cvss_score, asset_criticality=None, exploitability=None):
    base = cvss_score or 0.0
    multiplier = 1.0
    if asset_criticality == 'critical':
        multiplier *= 1.5
    elif asset_criticality == 'high':
        multiplier *= 1.2
    if exploitability:
        multiplier *= 1.1
    return min(10.0, round(base * multiplier, 1))


def calculate_priority(cvss_score, asset_criticality=None):
    risk = calculate_risk_score(cvss_score, asset_criticality)
    if risk >= 9.0:
        return 'CRITICAL'
    elif risk >= 7.0:
        return 'HIGH'
    elif risk >= 4.0:
        return 'MEDIUM'
    elif risk >= 0.1:
        return 'LOW'
    return 'INFO'


def calculate_due_at(priority):
    hours = PRIORITY_SLA_HOURS.get(priority, 168)
    return timezone.now() + timedelta(hours=hours)


def is_overdue(case):
    if not case.due_at:
        return False
    return timezone.now() > case.due_at and case.status not in ('RESOLVED', 'RISK_ACCEPTED', 'FALSE_POSITIVE')


def get_sla_remaining(case):
    if not case.due_at:
        return None
    remaining = case.due_at - timezone.now()
    return remaining.total_seconds()
