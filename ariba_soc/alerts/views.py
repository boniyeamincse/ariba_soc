import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib.auth.models import User
from settings_manager.models import SeveritySettings, StatusSettings, VerdictSettings
from .models import Alert, AlertComment, AlertAuditLog, Notification
from .forms import AlertEditForm, AlertCommentForm
from .services import update_alert, assign_alert, create_audit_log, _notify_escalation


def check_perm(user, perm):
    profile = getattr(user, 'analyst_profile', None)
    if not profile or not profile.has_permission(perm):
        raise PermissionDenied(f"You don't have permission: {perm}")


@login_required
def alert_table(request):
    alerts = Alert.objects.select_related('assignee', 'source').all()
    severity = request.GET.get('severity')
    status = request.GET.get('status')
    verdict = request.GET.get('verdict')
    search = request.GET.get('search')
    assignee = request.GET.get('assignee')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    sort = request.GET.get('sort', '-alert_time')

    if search:
        alerts = alerts.filter(
            Q(alert_name__icontains=search) |
            Q(wazuh_alert_id__icontains=search) |
            Q(hostname__icontains=search) |
            Q(username__icontains=search) |
            Q(source_ip__icontains=search) |
            Q(destination_ip__icontains=search) |
            Q(rule_id__icontains=search) |
            Q(agent_name__icontains=search) |
            Q(process_name__icontains=search) |
            Q(file_hash_md5__icontains=search) |
            Q(file_hash_sha256__icontains=search)
        )
    if severity:
        alerts = alerts.filter(severity=severity)
    if status:
        alerts = alerts.filter(status=status)
    if verdict:
        alerts = alerts.filter(verdict=verdict)
    if assignee:
        alerts = alerts.filter(assignee_id=assignee)
    if date_from:
        alerts = alerts.filter(alert_time__gte=date_from)
    if date_to:
        alerts = alerts.filter(alert_time__lte=date_to)

    allowed_sorts = ['alert_time', '-alert_time', 'severity', '-severity', 'status', '-status', 'verdict', '-verdict', 'alert_name', '-alert_name', 'wazuh_alert_id', '-wazuh_alert_id']
    if sort in allowed_sorts:
        alerts = alerts.order_by(sort)
    else:
        alerts = alerts.order_by('-alert_time')

    paginator = Paginator(alerts, 25)
    page = request.GET.get('page', 1)
    alerts_page = paginator.get_page(page)

    assignees = Alert.objects.exclude(assignee__isnull=True).values_list('assignee_id', 'assignee__username').distinct()

    context = {
        'alerts': alerts_page,
        'assignees': assignees,
        'users': User.objects.filter(is_active=True),
        'severities': SeveritySettings.objects.filter(is_active=True).order_by('sort_order'),
        'statuses': StatusSettings.objects.filter(is_active=True).order_by('sort_order'),
        'verdicts': VerdictSettings.objects.filter(is_active=True).order_by('name'),
        'current_filters': {
            'search': search, 'severity': severity, 'status': status,
            'verdict': verdict, 'assignee': assignee, 'date_from': date_from, 'date_to': date_to,
        },
        'is_paginated': alerts_page.has_other_pages(),
    }
    return render(request, 'ariba_soc/alert_table.html', context)


@login_required
def alert_board(request):
    alerts = Alert.objects.select_related('assignee', 'source').all()

    now = timezone.now()
    month = request.GET.get('month')
    year = request.GET.get('year')

    if month and year:
        try:
            m, y = int(month), int(year)
            alerts = alerts.filter(alert_time__year=y, alert_time__month=m)
        except (ValueError, TypeError):
            month = None
            year = None
    else:
        month = now.month
        year = now.year
        alerts = alerts.filter(alert_time__year=year, alert_time__month=month)

    search = request.GET.get('search')
    if search:
        alerts = alerts.filter(
            Q(alert_name__icontains=search) |
            Q(hostname__icontains=search) |
            Q(username__icontains=search)
        )
    context = {
        'new_alerts': alerts.filter(status='New'),
        'in_progress_alerts': alerts.filter(status='In Progress'),
        'awaiting_alerts': alerts.filter(status='Awaiting Action'),
        'pending_alerts': alerts.filter(status='Pending'),
        'escalated_alerts': alerts.filter(status__startswith='Escalated'),
        'true_positives': alerts.filter(verdict='True Positive', status='Closed'),
        'false_positives': alerts.filter(verdict='False Positive', status='Closed'),
        'closed_alerts': alerts.filter(status='Closed'),
        'archived_alerts': alerts.filter(status='Archived'),
        'users': User.objects.filter(is_active=True),
        'selected_month': month,
        'selected_year': year,
        'months': [
            (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
            (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
            (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December'),
        ],
        'years': range(2024, 2028),
    }
    return render(request, 'ariba_soc/alert_board.html', context)


@login_required
def alert_detail(request, alert_id):
    alert = get_object_or_404(Alert.objects.select_related('assignee', 'source', 'assigned_by'), id=alert_id)
    comments = alert.comments.select_related('user').all()
    audit_logs = alert.audit_logs.select_related('user').all()[:50]
    form = AlertEditForm(instance=alert, user=request.user)
    return render(request, 'ariba_soc/alert_detail.html', {
        'alert': alert, 'comments': comments, 'audit_logs': audit_logs, 'form': form,
        'users': User.objects.filter(is_active=True),
    })


@login_required
def alert_edit(request, alert_id):
    alert = get_object_or_404(Alert, id=alert_id)
    if request.method == 'POST':
        form = AlertEditForm(request.POST, instance=alert, user=request.user)
        if form.is_valid():
            changed = []
            for field in ('severity', 'status', 'verdict'):
                if field in form.changed_data:
                    perm_map = {'severity': 'can_change_severity', 'status': 'can_change_status', 'verdict': 'can_change_verdict'}
                    check_perm(request.user, perm_map[field])
                    changed.append(field)
            update_alert(alert, form, request.user, request)
            messages.success(request, 'Alert updated successfully.')
            return redirect('alerts:detail', alert_id=alert.id)
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    return redirect('alerts:detail', alert_id=alert_id)


@login_required
@require_POST
def alert_assign(request, alert_id):
    alert = get_object_or_404(Alert, id=alert_id)
    assignee_id = request.POST.get('assignee_id')
    assignee = request.user
    if assignee_id:
        check_perm(request.user, 'can_assign_others')
        assignee = get_object_or_404(User, id=assignee_id)
    else:
        check_perm(request.user, 'can_assign_self')
    assign_alert(alert, request.user, assignee, request)
    messages.success(request, f'Alert assigned to {assignee.username}.')
    return redirect(request.META.get('HTTP_REFERER', 'alerts:table'))


@login_required
@require_POST
def alert_add_comment(request, alert_id):
    alert = get_object_or_404(Alert, id=alert_id)
    form = AlertCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.alert = alert
        comment.user = request.user
        comment.comment_type = 'Analyst Note'
        comment.save()
        create_audit_log(alert, request.user, 'Comment Added', '', form.cleaned_data['comment'][:200], request)
        messages.success(request, 'Comment added.')
    return redirect('alerts:detail', alert_id=alert_id)


ESCALATION_TIERS = {
    'l2': 'Escalated to L2',
    'irit': 'Escalated to IR/IT',
    'management': 'Escalated to Management',
}


@login_required
def alert_escalate(request, alert_id):
    check_perm(request.user, 'can_escalate_alert')
    alert = get_object_or_404(Alert, id=alert_id)
    if request.method == 'POST':
        reason = request.POST.get('escalation_reason', '')
        tier = request.POST.get('tier', 'l2')
        if not reason:
            messages.error(request, 'Escalation reason is required.')
            return redirect('alerts:detail', alert_id=alert_id)
        target_status = ESCALATION_TIERS.get(tier, 'Escalated to L2')
        alert.status = target_status
        alert.is_escalated = True
        alert.escalated_at = alert.escalated_at or timezone.now()
        alert.escalation_reason = reason
        alert.save()
        AlertComment.objects.create(
            alert=alert, user=request.user, comment=f"{target_status}: {reason}", comment_type='Escalation Note'
        )
        create_audit_log(alert, request.user, 'Escalated', '', f'{target_status}: {reason}', request)
        _notify_escalation(alert, f'{target_status} — {reason}')
        messages.success(request, f'Alert escalated: {target_status}.')
    return redirect('alerts:detail', alert_id=alert_id)


@login_required
def alert_close(request, alert_id):
    check_perm(request.user, 'can_close_alert')
    alert = get_object_or_404(Alert, id=alert_id)
    if request.method == 'POST':
        verdict = request.POST.get('verdict', '')
        comment = request.POST.get('closure_comment', '')
        if not verdict or verdict == 'None':
            messages.error(request, 'Verdict must be set before closing.')
            return redirect('alerts:detail', alert_id=alert_id)
        if not comment:
            messages.error(request, 'Closure comment is required.')
            return redirect('alerts:detail', alert_id=alert_id)
        old_status = alert.status
        alert.status = 'Closed'
        alert.verdict = verdict
        alert.closure_reason = comment
        alert.save()
        AlertComment.objects.create(
            alert=alert, user=request.user, comment=comment, comment_type='Closure Note'
        )
        create_audit_log(alert, request.user, 'Closed', old_status, verdict, request)
        messages.success(request, 'Alert closed.')
    return redirect('alerts:detail', alert_id=alert_id)


@login_required
@require_POST
def alert_archive(request, alert_id):
    check_perm(request.user, 'can_archive')
    alert = get_object_or_404(Alert, id=alert_id)
    alert.status = 'Archived'
    alert.save()
    create_audit_log(alert, request.user, 'Archived', '', 'Archived', request)
    messages.success(request, 'Alert archived.')
    return redirect('alerts:table')


@login_required
@require_POST
def alert_reopen(request, alert_id):
    alert = get_object_or_404(Alert, id=alert_id)
    if alert.status not in ('Closed', 'Archived'):
        messages.error(request, 'Only closed or archived alerts can be reopened.')
        return redirect('alerts:detail', alert_id=alert_id)
    old_status = alert.status
    alert.status = 'New'
    alert.closed_at = None
    alert.archived_at = None
    alert.closure_reason = ''
    alert.save()
    create_audit_log(alert, request.user, 'Reopened', old_status, 'New', request)
    messages.success(request, 'Alert reopened.')
    return redirect('alerts:detail', alert_id=alert_id)


@login_required
def my_alerts(request):
    alerts = Alert.objects.filter(assignee=request.user).select_related('source')
    if not alerts.exists():
        return render(request, 'ariba_soc/my_alerts.html', {'alerts': alerts, 'no_alerts': True, 'users': User.objects.filter(is_active=True)})
    paginator = Paginator(alerts, 50)
    page = request.GET.get('page', 1)
    alerts_page = paginator.get_page(page)
    return render(request, 'ariba_soc/my_alerts.html', {'alerts': alerts_page, 'users': User.objects.filter(is_active=True)})


@login_required
def alerts_api(request):
    data = list(Alert.objects.select_related('assignee').only(
        'id', 'alert_name', 'severity', 'status', 'verdict', 'priority',
        'assignee_id', 'source_name', 'hostname', 'alert_time', 'rule_id', 'sla_status'
    ).order_by('-alert_time')[:100].values(
        'id', 'alert_name', 'severity', 'status', 'verdict', 'priority',
        'assignee__username', 'source_name', 'hostname', 'alert_time', 'rule_id', 'sla_status'
    ))
    return JsonResponse({'alerts': data})


@login_required
def mark_notifications_read(request):
    if request.method == 'POST':
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
@require_POST
def alert_bulk_action(request):
    action = request.POST.get('action')
    value = request.POST.get('value', '')
    alert_ids = request.POST.getlist('alert_ids')
    if not alert_ids or not action:
        messages.error(request, 'No alerts selected or no action specified.')
        return redirect('alerts:table')
    alerts = Alert.objects.filter(id__in=alert_ids)
    count = alerts.count()
    if action == 'assign':
        check_perm(request.user, 'can_assign_others')
        user_id = value
        if user_id:
            assignee = get_object_or_404(User, id=user_id)
            for alert in alerts:
                assign_alert(alert, request.user, assignee, request)
        messages.success(request, f'{count} alerts assigned.')
    elif action == 'status':
        check_perm(request.user, 'can_change_status')
        old_val = ', '.join(alerts.values_list('status', flat=True).distinct())
        alerts.update(status=value)
        for alert in alerts:
            create_audit_log(alert, request.user, 'Status Changed', old_val, value, request)
        messages.success(request, f'{count} alerts status changed to {value}.')
    elif action == 'verdict':
        check_perm(request.user, 'can_change_verdict')
        old_val = ', '.join(alerts.values_list('verdict', flat=True).distinct())
        alerts.update(verdict=value)
        for alert in alerts:
            create_audit_log(alert, request.user, 'Verdict Changed', old_val, value, request)
        messages.success(request, f'{count} alerts verdict changed to {value}.')
    elif action == 'close':
        check_perm(request.user, 'can_close_alert')
        old_val = ', '.join(alerts.values_list('status', flat=True).distinct())
        for alert in alerts:
            alert.status = 'Closed'
            alert.verdict = value or 'None'
            alert.closed_at = timezone.now()
            alert.save()
            create_audit_log(alert, request.user, 'Closed', old_val, value, request)
        messages.success(request, f'{count} alerts closed.')
    elif action == 'archive':
        check_perm(request.user, 'can_archive')
        alerts.update(status='Archived')
        for alert in alerts:
            create_audit_log(alert, request.user, 'Archived', '', 'Archived', request)
        messages.success(request, f'{count} alerts archived.')
    else:
        messages.error(request, f'Unknown action: {action}')
    return redirect('alerts:table')


@login_required
@require_POST
def alert_move_api(request, alert_id):
    alert = get_object_or_404(Alert, id=alert_id)
    data = json.loads(request.body)
    new_status = data.get('status')
    if new_status and StatusSettings.objects.filter(name=new_status, is_active=True).exists():
        old = alert.status
        alert.status = new_status
        if new_status == 'In Progress':
            alert.acknowledged_at = alert.acknowledged_at or timezone.now()
        alert.save()
        create_audit_log(alert, request.user, 'Status Changed', old, new_status, request)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
