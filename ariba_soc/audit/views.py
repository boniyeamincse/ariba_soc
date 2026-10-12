from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from alerts.models import AlertAuditLog
from settings_manager.models import SettingAuditLog


@login_required
def audit_log_list(request):
    log_type = request.GET.get('type', 'alerts')
    search_q = request.GET.get('q', '').strip()
    action_filter = request.GET.get('action', '').strip()
    page = request.GET.get('page', 1)

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if log_type == 'settings':
        qs = SettingAuditLog.objects.select_related('user').all().order_by('-created_at')
        if search_q:
            qs = qs.filter(
                Q(action__icontains=search_q) |
                Q(model_name__icontains=search_q) |
                Q(user__username__icontains=search_q) |
                Q(old_value__icontains=search_q) |
                Q(new_value__icontains=search_q) |
                Q(ip_address__icontains=search_q)
            )
        if action_filter:
            qs = qs.filter(action=action_filter)
        
        actions_list = SettingAuditLog.objects.values_list('action', flat=True).distinct()[:20]
        total_count = qs.count()
        today_count = SettingAuditLog.objects.filter(created_at__gte=today_start).count()
        unique_users = SettingAuditLog.objects.values('user').distinct().count()
    else:
        qs = AlertAuditLog.objects.select_related('user', 'alert').all().order_by('-created_at')
        if search_q:
            qs = qs.filter(
                Q(action__icontains=search_q) |
                Q(alert__alert_name__icontains=search_q) |
                Q(user__username__icontains=search_q) |
                Q(old_value__icontains=search_q) |
                Q(new_value__icontains=search_q) |
                Q(ip_address__icontains=search_q)
            )
        if action_filter:
            qs = qs.filter(action=action_filter)
        
        actions_list = [a[0] for a in AlertAuditLog.ACTIONS]
        total_count = qs.count()
        today_count = AlertAuditLog.objects.filter(created_at__gte=today_start).count()
        unique_users = AlertAuditLog.objects.values('user').distinct().count()

    paginator = Paginator(qs, 50)
    logs_page = paginator.get_page(page)

    ctx = {
        'section': 'audit',
        'log_type': log_type,
        'logs': logs_page,
        'search_q': search_q,
        'action_filter': action_filter,
        'actions_list': actions_list,
        'total_count': total_count,
        'today_count': today_count,
        'unique_users': unique_users,
    }
    return render(request, 'ariba_soc/audit_logs.html', ctx)
