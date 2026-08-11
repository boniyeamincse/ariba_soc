from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q, Avg, F
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from alerts.models import Alert


@login_required
def dashboard_home(request):
    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    context = {
        'total_alerts_today': Alert.objects.filter(alert_time__gte=today).count(),
        'open_alerts': Alert.objects.filter(status__in=['New', 'Awaiting Action', 'In Progress', 'Pending']).count(),
        'critical_open': Alert.objects.filter(severity='Critical', status__in=['New', 'Awaiting Action', 'In Progress']).count(),
        'true_positives': Alert.objects.filter(verdict='True Positive').count(),
        'false_positives': Alert.objects.filter(verdict='False Positive').count(),
        'escalated_alerts': Alert.objects.filter(status='Escalated').count(),
        'closed_alerts': Alert.objects.filter(status='Closed').count(),
        'sla_breached': Alert.objects.filter(sla_status='Breached').count(),
        'total_alerts_week': Alert.objects.filter(alert_time__gte=week_ago).count(),
        'total_alerts_month': Alert.objects.filter(alert_time__gte=month_ago).count(),
        'users': User.objects.filter(is_active=True),
    }
    return render(request, 'ariba_soc/dashboard_home.html', context)


@login_required
def dashboard_stats_api(request):
    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
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
