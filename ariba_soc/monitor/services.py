"""Data computation for the monitor wallboard. Every function here reads
real data from existing models -- nothing on the wallboard is hardcoded
or faked. Filled in incrementally: Phase 2 (live ops), Phase 3
(executive), Phase 4 (globe geo-lookup).
"""
import logging
from datetime import timedelta
import requests
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Count, Q, Avg, F
from django.utils import timezone
from alerts.models import Alert
from settings_manager.models import SystemSetting

logger = logging.getLogger(__name__)

OPEN_STATUSES = ['New', 'Awaiting Action', 'In Progress', 'Pending',
                  'Escalated to L2', 'Escalated to IR/IT', 'Escalated to Management', 'Remediation']

# The Wazuh manager monitors itself (and, depending on setup, its own
# neighbor containers) as part of its own CIS-benchmark/vulnerability
# ruleset. That's legitimate self-monitoring data, but it's not a real
# "attacked asset" on the org's estate -- showing it as one on the
# wallboard is misleading. Excluded from both attacked-asset widgets by
# default; admin can extend the list via System Settings without a
# code change.
DEFAULT_OWN_INFRA_HOSTNAMES = ['wazuh.manager', 'wazuh.indexer', 'wazuh.dashboard']


def _own_infra_hostnames():
    extra = SystemSetting.get_setting('wallboard_excluded_hostnames', '')
    extra_list = [h.strip() for h in extra.split(',') if h.strip()]
    return DEFAULT_OWN_INFRA_HOSTNAMES + extra_list

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
            .exclude(hostname__in=_own_infra_hostnames())
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


# ---- Executive section ----

def health_score():
    """Simple weighted deduction off real counts, clamped 0-100. Not a
    formal industry formula -- a readable, defensible approximation:
    each open Critical costs 10 points, each open High costs 5, each SLA
    breach costs 8, each alert escalated to Management costs 6."""
    open_critical = Alert.objects.filter(severity='Critical', status__in=OPEN_STATUSES).count()
    open_high = Alert.objects.filter(severity='High', status__in=OPEN_STATUSES).count()
    sla_breached = Alert.objects.filter(sla_status='Breached', status__in=OPEN_STATUSES).count()
    mgmt_escalated = Alert.objects.filter(status='Escalated to Management').exclude(status__in=['Closed', 'Archived']).count()
    score = 100 - (open_critical * 10 + open_high * 5 + sla_breached * 8 + mgmt_escalated * 6)
    return max(0, min(100, score))


def today_severity_counts():
    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    qs = Alert.objects.filter(alert_time__gte=today)
    return {
        'critical': qs.filter(severity='Critical').count(),
        'high': qs.filter(severity='High').count(),
    }


def resolved_vs_unresolved():
    resolved = Alert.objects.filter(status__in=['Closed', 'Archived']).count()
    unresolved = Alert.objects.filter(status__in=OPEN_STATUSES).count()
    return {'resolved': resolved, 'unresolved': unresolved}


def threat_trend(days=7):
    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    out = []
    for i in range(days - 1, -1, -1):
        start = today - timedelta(days=i)
        end = start + timedelta(days=1)
        out.append({'date': start.strftime('%Y-%m-%d'), 'count': Alert.objects.filter(alert_time__gte=start, alert_time__lt=end).count()})
    return out


def most_targeted_systems(limit=6):
    """All-time, unlike Live Ops' top_attacked_assets which is open-alerts-only
    -- this is meant to show the strategic pattern, not the operational one."""
    rows = (Alert.objects
            .exclude(hostname='')
            .exclude(hostname__in=_own_infra_hostnames())
            .values('hostname')
            .annotate(count=Count('id'))
            .order_by('-count')[:limit])
    return list(rows)


def incident_response_time():
    """Average minutes from alert_time to acknowledged_at, over alerts that
    have actually been acknowledged (i.e. someone worked it)."""
    qs = Alert.objects.filter(acknowledged_at__isnull=False).annotate(
        response_seconds=F('acknowledged_at') - F('alert_time')
    )
    avg = qs.aggregate(avg=Avg('response_seconds'))['avg']
    return round(avg.total_seconds() / 60, 1) if avg else None


def sla_status_breakdown():
    rows = Alert.objects.filter(status__in=OPEN_STATUSES).values('sla_status').annotate(count=Count('id'))
    counts = {r['sla_status']: r['count'] for r in rows}
    return [{'sla_status': s, 'count': counts.get(s, 0)} for s in ('Within SLA', 'Near SLA breach', 'Breached')]


def monthly_comparison():
    now = timezone.now()
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_end = this_month_start - timedelta(seconds=1)
    last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    this_month_total = Alert.objects.filter(alert_time__gte=this_month_start).count()
    last_month_total = Alert.objects.filter(alert_time__gte=last_month_start, alert_time__lte=last_month_end).count()
    this_month_resolved = Alert.objects.filter(alert_time__gte=this_month_start, status__in=['Closed', 'Archived']).count()
    last_month_resolved = Alert.objects.filter(alert_time__gte=last_month_start, alert_time__lte=last_month_end, status__in=['Closed', 'Archived']).count()

    return {
        'this_month_total': this_month_total, 'last_month_total': last_month_total,
        'this_month_resolved': this_month_resolved, 'last_month_resolved': last_month_resolved,
    }


def wazuh_tool_status():
    cached = cache.get('wallboard_wazuh_status')
    if cached is not None:
        return cached
    try:
        from wazuh_integration.services import ManagerClient
        result = ManagerClient().get_manager_status()
        status = 'Down' if 'error' in result else 'Operational'
    except Exception:
        status = 'Unknown'
    cache.set('wallboard_wazuh_status', status, 30)
    return status


# ---- Attack globe ----

def geolocate_ip(ip):
    """Free IP->lat/long lookup (ip-api.com, no key required), cached 7
    days per IP in Redis so a live-polling wallboard doesn't hammer a
    free rate-limited API. Returns None for private/reserved IPs (can't
    be plotted on a world map) or lookup failures."""
    import ipaddress
    try:
        if ipaddress.ip_address(ip).is_private:
            return None
    except ValueError:
        return None

    cache_key = f'wallboard_geoip_{ip}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached or None

    try:
        resp = requests.get(f'http://ip-api.com/json/{ip}', timeout=3)
        data = resp.json()
        if data.get('status') != 'success':
            cache.set(cache_key, False, 60 * 60 * 24 * 7)
            return None
        result = {'lat': data['lat'], 'lon': data['lon'], 'city': data.get('city', ''), 'country': data.get('country', '')}
        cache.set(cache_key, result, 60 * 60 * 24 * 7)
        return result
    except Exception as e:
        logger.warning(f'geolocate_ip failed for {ip}: {e}')
        return None


def resolve_globe_arcs(limit=50):
    """Distinct source IPs from recent open alerts -> geolocated arc
    points. Capped at `limit` distinct IPs per call regardless of cache
    state, to stay well under ip-api.com's free-tier rate limit even
    on a cold cache."""
    rows = (Alert.objects
            .exclude(source_ip__isnull=True)
            .filter(status__in=OPEN_STATUSES)
            .values('source_ip')
            .annotate(count=Count('id'))
            .order_by('-count')[:limit])

    arcs = []
    for row in rows:
        ip = row['source_ip']
        geo = geolocate_ip(ip)
        if not geo:
            continue
        top_alert = (Alert.objects.filter(source_ip=ip, status__in=OPEN_STATUSES)
                     .order_by('-severity_score').first())
        arcs.append({
            'ip': ip, 'lat': geo['lat'], 'lon': geo['lon'],
            'city': geo['city'], 'country': geo['country'],
            'count': row['count'],
            'severity': top_alert.severity if top_alert else 'Low',
        })
    return arcs


def wallboard_executive():
    return {
        'health_score': health_score(),
        'today': today_severity_counts(),
        'incidents_count': len(active_incidents(limit=1000)),
        'resolved_vs_unresolved': resolved_vs_unresolved(),
        'threat_trend': threat_trend(),
        'most_targeted': most_targeted_systems(),
        'response_time_minutes': incident_response_time(),
        'sla_breakdown': sla_status_breakdown(),
        'monthly': monthly_comparison(),
        'tool_status': {'Wazuh': wazuh_tool_status()},
    }
