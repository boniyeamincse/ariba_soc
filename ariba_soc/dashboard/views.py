from datetime import timedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q, Avg, F
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.cache import cache_page
from alerts.models import Alert, AlertAuditLog, AlertEscalation
from accounts.decorators import role_required, minimum_soc_tier, role_has_dashboard_access


OPEN_WORKFLOW_STATES = [
    'QUEUED_L1', 'IN_PROGRESS_L1', 'PENDING_L2_ACCEPTANCE', 'IN_PROGRESS_L2',
    'RETURNED_TO_L1', 'PENDING_L3_ACCEPTANCE', 'IN_PROGRESS_L3', 'RETURNED_TO_L2',
    'INCIDENT', 'REOPENED',
]

OPEN_STATUSES = ['New', 'Awaiting Action', 'In Progress', 'Pending',
                  'Escalated to L2', 'Escalated to L3', 'Escalated to IR/IT',
                  'Escalated to Management', 'Remediation']

NOW = lambda: timezone.now()
TODAY = lambda: NOW().replace(hour=0, minute=0, second=0, microsecond=0)
WEEK_AGO = lambda: TODAY() - timedelta(days=7)
MONTH_AGO = lambda: TODAY() - timedelta(days=30)


@login_required
def dashboard_home(request):
    role = getattr(request.user.analyst_profile, 'role', '')
    if role == 'MONITOR':
        return render(request, 'monitor/wallboard.html')
    return dashboard_manager(request)


@login_required
@role_required('L1', 'L2', 'L3', 'SOC_MGR', 'ADMIN', 'VIEWER', 'SOC_ENG')
def dashboard_l1(request):
    user = request.user
    profile = user.analyst_profile
    role = profile.role

    new_l1_queue = Alert.objects.filter(
        workflow_state='QUEUED_L1',
    ).select_related('assignee', 'source').order_by('-alert_time')[:20]

    my_investigations = Alert.objects.filter(
        assignee=user,
        workflow_state='IN_PROGRESS_L1',
    ).select_related('source').order_by('-alert_time')[:20]

    returned_from_l2 = Alert.objects.filter(
        workflow_state='RETURNED_TO_L1',
    ).select_related('assignee', 'source').order_by('-returned_at')[:20]

    critical_high = Alert.objects.filter(
        severity__in=['Critical', 'High'],
        workflow_state__in=['QUEUED_L1', 'IN_PROGRESS_L1'],
    ).select_related('assignee', 'source').order_by('-alert_time')[:20]

    sla_near_breach = Alert.objects.filter(
        sla_status='Near SLA breach',
        workflow_state__in=OPEN_WORKFLOW_STATES,
    ).select_related('assignee').order_by('sla_due_at')[:10]

    sla_breached = Alert.objects.filter(
        sla_status='Breached',
        workflow_state__in=OPEN_WORKFLOW_STATES,
    ).select_related('assignee').order_by('sla_due_at')[:10]

    recently_escalated_l2 = Alert.objects.filter(
        workflow_state='PENDING_L2_ACCEPTANCE',
    ).select_related('assignee', 'source').order_by('-escalated_at')[:10]

    needs_escalation = Alert.objects.filter(
        severity__in=['Critical', 'High'],
        workflow_state='IN_PROGRESS_L1',
    ).select_related('assignee').order_by('sla_due_at')[:10]

    today = TODAY()
    week_ago = WEEK_AGO()
    shift_stats = {
        'total_today': Alert.objects.filter(alert_time__gte=today).count(),
        'closed_today': Alert.objects.filter(
            workflow_state__in=['CLOSED', 'RESOLVED'], status_updated_at__gte=today,
        ).count(),
        'escalated_today': Alert.objects.filter(
            workflow_state='PENDING_L2_ACCEPTANCE', escalated_at__gte=today,
        ).count(),
        'avg_response_today': _avg_response_time(today),
        'weekly_total': Alert.objects.filter(alert_time__gte=week_ago).count(),
    }

    context = {
        'new_l1_queue': new_l1_queue,
        'my_investigations': my_investigations,
        'returned_from_l2': returned_from_l2,
        'critical_high': critical_high,
        'sla_near_breach': sla_near_breach,
        'sla_breached': sla_breached,
        'recently_escalated_l2': recently_escalated_l2,
        'needs_escalation': needs_escalation,
        'shift_stats': shift_stats,
        'dashboard_title': 'SOC L1 Dashboard',
        'dashboard_level': 'L1',
        'role': role,
    }
    return render(request, 'ariba_soc/dashboard_l1.html', context)


@login_required
@role_required('L2', 'L3', 'SOC_MGR', 'ADMIN', 'SOC_ENG')
def dashboard_l2(request):
    user = request.user

    pending_l2_acceptance = Alert.objects.filter(
        workflow_state='PENDING_L2_ACCEPTANCE',
    ).select_related('assignee', 'accepted_by', 'source').order_by('-escalated_at')[:20]

    my_investigations = Alert.objects.filter(
        assignee=user,
        workflow_state='IN_PROGRESS_L2',
    ).select_related('source').order_by('-accepted_at')[:20]

    active_investigations = Alert.objects.filter(
        workflow_state='IN_PROGRESS_L2',
    ).select_related('assignee').order_by('-accepted_at')[:20]

    returned_to_l1 = Alert.objects.filter(
        workflow_state='RETURNED_TO_L1',
        escalated_from_tier='L2',
    ).select_related('returned_by').order_by('-returned_at')[:10]

    pending_escalation_l3 = Alert.objects.filter(
        workflow_state='PENDING_L3_ACCEPTANCE',
    ).select_related('assignee').order_by('-escalated_at')[:10]

    incident_candidates = Alert.objects.filter(
        is_incident_candidate=True,
        workflow_state__in=['IN_PROGRESS_L2', 'PENDING_L3_ACCEPTANCE'],
    ).select_related('assignee').order_by('-alert_time')[:10]

    sla_near_breach = Alert.objects.filter(
        sla_status='Near SLA breach',
        workflow_state__in=['PENDING_L2_ACCEPTANCE', 'IN_PROGRESS_L2'],
    ).select_related('assignee').order_by('sla_due_at')[:10]

    sla_breached = Alert.objects.filter(
        sla_status='Breached',
        workflow_state__in=['PENDING_L2_ACCEPTANCE', 'IN_PROGRESS_L2'],
    ).select_related('assignee').order_by('sla_due_at')[:10]

    today = TODAY()
    week_ago = WEEK_AGO()
    l2_stats = {
        'pending_acceptance': Alert.objects.filter(workflow_state='PENDING_L2_ACCEPTANCE').count(),
        'accepted_today': Alert.objects.filter(
            workflow_state='IN_PROGRESS_L2', accepted_at__gte=today,
        ).count(),
        'returned_this_week': Alert.objects.filter(
            workflow_state='RETURNED_TO_L1', escalated_from_tier='L2', returned_at__gte=week_ago,
        ).count(),
        'avg_investigation_time': _avg_investigation_time('L2'),
        'active_count': Alert.objects.filter(workflow_state='IN_PROGRESS_L2').count(),
    }

    context = {
        'pending_l2_acceptance': pending_l2_acceptance,
        'my_investigations': my_investigations,
        'active_investigations': active_investigations,
        'returned_to_l1': returned_to_l1,
        'pending_escalation_l3': pending_escalation_l3,
        'incident_candidates': incident_candidates,
        'sla_near_breach': sla_near_breach,
        'sla_breached': sla_breached,
        'l2_stats': l2_stats,
        'dashboard_title': 'SOC L2 Dashboard',
        'dashboard_level': 'L2',
    }
    return render(request, 'ariba_soc/dashboard_l2.html', context)


@login_required
@role_required('L3', 'SOC_MGR', 'ADMIN', 'SOC_ENG')
def dashboard_l3(request):
    user = request.user

    pending_l3_acceptance = Alert.objects.filter(
        workflow_state='PENDING_L3_ACCEPTANCE',
    ).select_related('assignee', 'accepted_by', 'source').order_by('-escalated_at')[:20]

    my_investigations = Alert.objects.filter(
        assignee=user,
        workflow_state='IN_PROGRESS_L3',
    ).select_related('source').order_by('-accepted_at')[:20]

    returned_to_l2 = Alert.objects.filter(
        workflow_state='RETURNED_TO_L2',
        escalated_from_tier='L3',
    ).select_related('returned_by').order_by('-returned_at')[:10]

    incident_candidates = Alert.objects.filter(
        workflow_state='INCIDENT',
    ).select_related('assignee').order_by('-alert_time')[:10]

    active_investigations = Alert.objects.filter(
        workflow_state='IN_PROGRESS_L3',
    ).select_related('assignee').order_by('-accepted_at')[:20]

    advanced_backlog = Alert.objects.filter(
        workflow_state='IN_PROGRESS_L3',
    ).select_related('assignee').order_by('-alert_time')[:20]

    rca_items = Alert.objects.filter(
        severity__in=['Critical', 'High'], verdict='True Positive',
        root_cause_summary='',
    ).select_related('assignee').order_by('-closed_at')[:10]

    detection_gaps = Alert.objects.filter(
        verdict='False Positive', status='Closed',
    ).values('alert_name').annotate(fp_count=Count('id')).filter(fp_count__gte=3).order_by('-fp_count')[:10]

    rule_tuning_backlog = Alert.objects.filter(
        verdict='False Positive', status='Closed',
    ).values('rule_id', 'alert_name').annotate(fp_count=Count('id')).filter(fp_count__gte=2).order_by('-fp_count')[:10]

    today = TODAY()
    week_ago = WEEK_AGO()
    month_ago = MONTH_AGO()
    l3_stats = {
        'pending_acceptance': Alert.objects.filter(workflow_state='PENDING_L3_ACCEPTANCE').count(),
        'active_incidents': Alert.objects.filter(workflow_state='INCIDENT').count(),
        'detection_gaps': Alert.objects.filter(
            verdict='False Positive', status='Closed', status_updated_at__gte=week_ago,
        ).count(),
        'root_causes_done': Alert.objects.filter(
            root_cause_summary__gt='', status_updated_at__gte=week_ago,
        ).count(),
        'lessons_learned_week': Alert.objects.filter(
            root_cause_summary__gt='', status_updated_at__gte=week_ago,
        ).count(),
    }

    context = {
        'pending_l3_acceptance': pending_l3_acceptance,
        'my_investigations': my_investigations,
        'returned_to_l2': returned_to_l2,
        'incident_candidates': incident_candidates,
        'active_investigations': active_investigations,
        'advanced_backlog': advanced_backlog,
        'rca_items': rca_items,
        'detection_gaps': detection_gaps,
        'rule_tuning_backlog': rule_tuning_backlog,
        'l3_stats': l3_stats,
        'dashboard_title': 'SOC L3 Dashboard',
        'dashboard_level': 'L3',
    }
    return render(request, 'ariba_soc/dashboard_l3.html', context)


@login_required
@role_required('SOC_MGR', 'ADMIN')
def dashboard_manager(request):
    user = request.user

    critical_open = Alert.objects.filter(
        severity='Critical', workflow_state__in=OPEN_WORKFLOW_STATES,
    ).select_related('assignee').order_by('-alert_time')[:20]
    high_open = Alert.objects.filter(
        severity='High', workflow_state__in=OPEN_WORKFLOW_STATES,
    ).select_related('assignee').order_by('-alert_time')[:20]
    sla_breached = Alert.objects.filter(
        sla_status='Breached', workflow_state__in=OPEN_WORKFLOW_STATES,
    ).select_related('assignee').order_by('sla_due_at')[:20]

    today = TODAY()
    week_ago = WEEK_AGO()
    month_ago = MONTH_AGO()

    risk_backlog = Alert.objects.filter(
        severity__in=['Critical', 'High'], workflow_state__in=OPEN_WORKFLOW_STATES,
    ).aggregate(
        total=Count('id'),
        critical_count=Count('id', filter=Q(severity='Critical')),
        high_count=Count('id', filter=Q(severity='High')),
    )

    incident_status = Alert.objects.filter(
        workflow_state__in=OPEN_WORKFLOW_STATES + ['INCIDENT'],
    ).values('workflow_state').annotate(count=Count('id')).order_by('-count')

    queue_age = Alert.objects.filter(
        workflow_state__in=OPEN_WORKFLOW_STATES,
    ).values('current_tier').annotate(count=Count('id'))

    analyst_workload = Alert.objects.filter(
        assignee__isnull=False, workflow_state__in=OPEN_WORKFLOW_STATES,
    ).values('assignee__username', 'assignee__analyst_profile__role').annotate(
        count=Count('id')
    ).order_by('-count')[:15]

    avg_response = _avg_response_time(week_ago)
    avg_resolve = _avg_resolve_time(week_ago)

    escalation_stats = Alert.objects.filter(
        escalated_at__gte=week_ago,
    ).aggregate(
        total_escalated=Count('id'),
        accepted=Count('id', filter=Q(escalation_status='accepted')),
        returned=Count('id', filter=Q(escalation_status='returned')),
    )

    fp_rate = Alert.objects.filter(
        status='Closed', status_updated_at__gte=month_ago,
    ).aggregate(
        total=Count('id'),
        fp=Count('id', filter=Q(verdict='False Positive')),
    )

    reopen_count = Alert.objects.filter(
        workflow_state='REOPENED', status_updated_at__gte=week_ago,
    ).exclude(created_at__gte=week_ago).count()

    source_health = Alert.objects.filter(
        alert_time__gte=week_ago,
    ).values('source_name').annotate(
        count=Count('id'),
        latest=Count('id'),
    ).order_by('-count')[:10]

    ingestion_freshness = Alert.objects.order_by('-alert_time').values('alert_time')[:1]

    context = {
        'critical_open': critical_open,
        'high_open': high_open,
        'sla_breached': sla_breached,
        'risk_backlog': risk_backlog,
        'incident_status': incident_status,
        'queue_age': queue_age,
        'analyst_workload': analyst_workload,
        'avg_response': avg_response,
        'avg_resolve': avg_resolve,
        'escalation_stats': escalation_stats,
        'fp_rate': fp_rate,
        'reopen_count': reopen_count,
        'source_health': source_health,
        'ingestion_freshness': ingestion_freshness[0] if ingestion_freshness else None,
        'today': today,
        'week_ago': week_ago,
        'dashboard_title': 'SOC Manager Dashboard',
        'dashboard_level': 'manager',
    }
    return render(request, 'ariba_soc/dashboard_manager.html', context)


def _avg_response_time(since):
    try:
        qs = Alert.objects.filter(acknowledged_at__isnull=False, acknowledged_at__gte=since).annotate(
            response_seconds=F('acknowledged_at') - F('alert_time')
        )
        avg = qs.aggregate(avg=Avg('response_seconds'))['avg']
        return round(avg.total_seconds() / 60, 1) if avg else None
    except Exception:
        qs = Alert.objects.filter(acknowledged_at__isnull=False, acknowledged_at__gte=since).values_list('alert_time', 'acknowledged_at')
        if not qs.exists():
            return None
        total = sum((ack - at).total_seconds() for at, ack in qs)
        return round(total / 60 / qs.count(), 1)


def _avg_resolve_time(since):
    try:
        qs = Alert.objects.filter(closed_at__isnull=False, closed_at__gte=since).annotate(
            resolve_seconds=F('closed_at') - F('alert_time')
        )
        avg = qs.aggregate(avg=Avg('resolve_seconds'))['avg']
        return round(avg.total_seconds() / 60, 1) if avg else None
    except Exception:
        qs = Alert.objects.filter(closed_at__isnull=False, closed_at__gte=since).values_list('alert_time', 'closed_at')
        if not qs.exists():
            return None
        total = sum((cl - at).total_seconds() for at, cl in qs)
        return round(total / 60 / qs.count(), 1)


def _avg_investigation_time(tier):
    try:
        qs = Alert.objects.filter(
            escalation_status='accepted', escalated_to_tier=tier, accepted_at__isnull=False
        ).annotate(
            investigation_seconds=F('accepted_at') - F('escalated_at')
        )
        avg = qs.aggregate(avg=Avg('investigation_seconds'))['avg']
        return round(avg.total_seconds() / 60, 1) if avg else None
    except Exception:
        qs = Alert.objects.filter(
            escalation_status='accepted', escalated_to_tier=tier, accepted_at__isnull=False
        ).values_list('escalated_at', 'accepted_at')
        if not qs.exists():
            return None
        total = sum((ac - es).total_seconds() for es, ac in qs)
        return round(total / 60 / qs.count(), 1)


@cache_page(60)
@login_required
def dashboard_stats_api(request):
    today = TODAY()
    days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]

    alerts_by_day = []
    for d in days:
        start = d.replace(hour=0, minute=0, second=0)
        end = start + timedelta(days=1)
        count = Alert.objects.filter(alert_time__gte=start, alert_time__lt=end).count()
        alerts_by_day.append({'date': d.strftime('%Y-%m-%d'), 'count': count})

    severity_data = Alert.objects.values('severity').annotate(count=Count('id'))
    status_data = Alert.objects.values('status').annotate(count=Count('id'))
    verdict_data = Alert.objects.values('verdict').annotate(count=Count('id'))

    top_alerts = Alert.objects.values('alert_name').annotate(count=Count('id')).order_by('-count')[:10]
    top_hosts = Alert.objects.exclude(hostname='').values('hostname').annotate(count=Count('id')).order_by('-count')[:10]
    analyst_load = Alert.objects.exclude(assignee__isnull=True).values('assignee__username').annotate(count=Count('id')).order_by('-count')[:10]

    return JsonResponse({
        'alerts_by_day': alerts_by_day,
        'severity': list(severity_data),
        'status': list(status_data),
        'verdict': list(verdict_data),
        'top_alerts': list(top_alerts),
        'top_hosts': list(top_hosts),
        'analyst_load': list(analyst_load),
    })
