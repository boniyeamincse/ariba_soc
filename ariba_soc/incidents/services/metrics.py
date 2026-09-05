from django.db.models import Count, Q, Avg, F
from django.utils import timezone
from datetime import timedelta
from incidents.models import Incident


def get_incident_metrics():
    now = timezone.now()
    total = Incident.objects.count()
    open_incidents = Incident.objects.exclude(
        status__in=['RESOLVED', 'CLOSED']
    ).count()
    critical_open = Incident.objects.filter(
        severity='CRITICAL'
    ).exclude(status__in=['RESOLVED', 'CLOSED']).count()
    awaiting_containment = Incident.objects.filter(
        status__in=['CONFIRMED', 'INVESTIGATING']
    ).count()
    in_recovery = Incident.objects.filter(
        status__in=['RECOVERY', 'MONITORING']
    ).count()
    oldest_unresolved = Incident.objects.exclude(
        status__in=['RESOLVED', 'CLOSED']
    ).order_by('detected_at').values_list('detected_at', flat=True).first()
    closed_this_month = Incident.objects.filter(
        status='CLOSED',
        closed_at__month=now.month,
        closed_at__year=now.year,
    ).count()

    resolved_incidents = Incident.objects.filter(
        resolved_at__isnull=False, detected_at__isnull=False
    )
    avg_resolution = resolved_incidents.annotate(
        duration=F('resolved_at') - F('detected_at')
    ).aggregate(avg=Avg('duration'))['avg']

    contained_incidents = Incident.objects.filter(
        contained_at__isnull=False, detected_at__isnull=False
    )
    avg_containment = contained_incidents.annotate(
        duration=F('contained_at') - F('detected_at')
    ).aggregate(avg=Avg('duration'))['avg']

    return {
        'total': total,
        'open_incidents': open_incidents,
        'critical_open': critical_open,
        'awaiting_containment': awaiting_containment,
        'in_recovery': in_recovery,
        'oldest_unresolved': oldest_unresolved,
        'closed_this_month': closed_this_month,
        'avg_time_to_containment': avg_containment,
        'avg_time_to_resolution': avg_resolution,
    }
