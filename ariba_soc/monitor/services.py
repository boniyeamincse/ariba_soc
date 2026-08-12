"""Data computation for the monitor wallboard. Every function here reads
real data from existing models -- nothing on the wallboard is hardcoded
or faked. Filled in incrementally: Phase 2 (live ops), Phase 3
(executive), Phase 4 (globe geo-lookup).
"""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from alerts.models import Alert

OPEN_STATUSES = ['New', 'Awaiting Action', 'In Progress', 'Pending',
                  'Escalated to L2', 'Escalated to IR/IT', 'Escalated to Management', 'Remediation']

User = get_user_model()


def live_open_count():
    return Alert.objects.filter(status__in=OPEN_STATUSES).count()


def severity_breakdown():
    rows = Alert.objects.filter(status__in=OPEN_STATUSES).values('severity').annotate(count=Count('id'))
    counts = {r['severity']: r['count'] for r in rows}
    return [{'severity': s, 'count': counts.get(s, 0)} for s in ('Critical', 'High', 'Medium', 'Low', 'Informational')]


def active_incidents(limit=8):
    """"Incidents" -- no separate Incident model exists, so this is derived
    directly from Alert: Critical/High severity that's escalated or still
    open, ranked most urgent (nearest SLA due date) first."""
    qs = (Alert.objects
          .filter(severity__in=['Critical', 'High'])
          .filter(Q(is_escalated=True) | Q(status__startswith='Escalated'))
          .exclude(status__in=['Closed', 'Archived'])
          .select_related('assignee')
          .order_by('sla_due_at'))
    return [{
        'id': a.id,
        'name': a.alert_name[:80],
        'severity': a.severity,
        'status': a.status,
        'hostname': a.hostname,
        'assignee': a.assignee.username if a.assignee else 'Unassigned',
        'sla_due_at': a.sla_due_at.isoformat() if a.sla_due_at else None,
        'sla_status': a.sla_status,
    } for a in qs[:limit]]


def top_attacked_assets(limit=6):
    rows = (Alert.objects
            .exclude(hostname='')
            .filter(status__in=OPEN_STATUSES)
            .values('hostname')
            .annotate(count=Count('id'))
            .order_by('-count')[:limit])
    return list(rows)


def online_analysts():
    """Approximation: last-login recency, not true presence (Django doesn't
    track per-request activity). A real "last active" would need a small
    activity-ping added later if this isn't precise enough."""
    cutoff = timezone.now() - timedelta(minutes=15)
    profiles = (User.objects
                .filter(is_active=True, last_login__gte=cutoff, analyst_profile__role__in=['L1', 'L2'])
                .select_related('analyst_profile')
                .order_by('username'))
    return [{'username': u.username, 'role': u.analyst_profile.role} for u in profiles]


def wallboard_live_ops():
    return {
        'live_open_count': live_open_count(),
        'severity_breakdown': severity_breakdown(),
        'incidents': active_incidents(),
        'top_assets': top_attacked_assets(),
        'online_analysts': online_analysts(),
    }
