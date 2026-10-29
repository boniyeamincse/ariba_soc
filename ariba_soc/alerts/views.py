import json
import os
import re
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.models import SocTeam
from settings_manager.models import SeveritySettings, StatusSettings, VerdictSettings
from accounts.decorators import role_required, permission_required, TIER_ORDER
from .models import (
    Alert, AlertComment, AlertAuditLog, Notification,
    AlertEscalation, AlertTransition, AlertBookmark, SavedFilter,
    AlertAttachment, AlertWatcher, FalsePositiveReport,
)
from .forms import AlertEditForm, AlertCommentForm
from .services import (
    update_alert, assign_alert, create_audit_log, _notify_escalation,
    find_related_alerts, merge_alerts, unmerge_alert,
)
from . import workflow


def check_perm(user, perm):
    profile = getattr(user, 'analyst_profile', None)
    if not profile or not profile.is_active:
        raise PermissionDenied('Your account is inactive.')
    if not profile.has_permission(perm):
        raise PermissionDenied(f"You don't have permission: {perm}")


def _handle_workflow_error(request, exc, alert_id=None):
    if exc.status_code == 409:
        messages.error(request, str(exc))
    elif exc.status_code == 403:
        messages.error(request, str(exc))
    else:
        messages.error(request, str(exc))
    if alert_id:
        return redirect('alerts:detail', alert_id=alert_id)
    return redirect('alerts:table')


@login_required
@permission_required('can_view_alerts')
def _apply_alert_filters(request):
    """Apply the alert-table querystring filters; return (queryset, filters, user_soc_team)."""
    alerts = Alert.objects.select_related('assignee', 'source', 'assigned_team').all()
    severity = request.GET.get('severity')
    status = request.GET.get('status')
    verdict = request.GET.get('verdict')
    search = request.GET.get('search')
    assignee = request.GET.get('assignee')
    team = request.GET.get('team')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    sort = request.GET.get('sort', '-alert_time')
    tag = request.GET.get('tag')
    bookmarked = request.GET.get('bookmarked')

    user_profile = getattr(request.user, 'analyst_profile', None)
    user_soc_team = user_profile.soc_team if user_profile else None

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
    if tag:
        alerts = alerts.filter(tags__contains=[tag])
    if bookmarked == '1':
        alerts = alerts.filter(bookmarks__user=request.user)
    if team:
        if team == 'my_team':
            if user_soc_team:
                alerts = alerts.filter(assigned_team=user_soc_team)
            else:
                alerts = alerts.none()
        elif team.isdigit():
            alerts = alerts.filter(assigned_team_id=int(team))
        elif team in ('L1', 'L2', 'L3', 'ENG', 'MGMT'):
            alerts = alerts.filter(assigned_team__tier=team)
    if date_from:
        alerts = alerts.filter(alert_time__gte=date_from)
    if date_to:
        alerts = alerts.filter(alert_time__lte=date_to)

    # Calculate severity KPI summary counts for the current scope (before filtering by severity)
    severity_summary = alerts.aggregate(
        total=Count('id'),
        critical=Count('id', filter=Q(severity__iexact='critical')),
        high=Count('id', filter=Q(severity__iexact='high')),
        medium=Count('id', filter=Q(severity__iexact='medium')),
        low=Count('id', filter=Q(severity__iexact='low')),
    )

    if severity:
        alerts = alerts.filter(severity__iexact=severity)

    allowed_sorts = ['alert_time', '-alert_time', 'severity', '-severity', 'status', '-status', 'verdict', '-verdict', 'alert_name', '-alert_name', 'wazuh_alert_id', '-wazuh_alert_id']
    if sort in allowed_sorts:
        alerts = alerts.order_by(sort)
    else:
        alerts = alerts.order_by('-alert_time')

    filters = {
        'search': search, 'severity': severity, 'status': status,
        'verdict': verdict, 'assignee': assignee, 'team': team,
        'date_from': date_from, 'date_to': date_to, 'sort': sort,
        'tag': tag, 'bookmarked': bookmarked,
    }
    return alerts, filters, user_soc_team, severity_summary


@login_required
@permission_required('can_view_alerts')
def alert_table(request):
    alerts, current_filters, user_soc_team, severity_summary = _apply_alert_filters(request)

    paginator = Paginator(alerts, 25)
    page = request.GET.get('page', 1)
    alerts_page = paginator.get_page(page)

    assignees = Alert.objects.exclude(assignee__isnull=True).values_list('assignee_id', 'assignee__username').distinct()
    soc_teams = SocTeam.objects.filter(is_active=True).order_by('tier', 'name')
    saved_filters = SavedFilter.objects.filter(Q(user=request.user) | Q(is_shared=True)).order_by('name')
    bookmarked_ids = set(AlertBookmark.objects.filter(user=request.user).values_list('alert_id', flat=True))
    for a in alerts_page:
        a.is_bookmarked = a.id in bookmarked_ids

    context = {
        'alerts': alerts_page,
        'assignees': assignees,
        'users': User.objects.filter(is_active=True),
        'soc_teams': soc_teams,
        'user_soc_team': user_soc_team,
        'severities': SeveritySettings.objects.filter(is_active=True).order_by('sort_order'),
        'statuses': StatusSettings.objects.filter(is_active=True).order_by('sort_order'),
        'verdicts': VerdictSettings.objects.filter(is_active=True).order_by('name'),
        'current_filters': current_filters,
        'saved_filters': saved_filters,
        'is_paginated': alerts_page.has_other_pages(),
        'severity_summary': severity_summary,
    }
    return render(request, 'ariba_soc/alert_table.html', context)


@login_required
@permission_required('can_view_alerts')
def alert_board(request):
    alerts = Alert.objects.select_related('assignee', 'source', 'assigned_team').all()

    team_param = request.GET.get('team')
    user_profile = getattr(request.user, 'analyst_profile', None)
    user_soc_team = user_profile.soc_team if user_profile else None

    if team_param == 'my_team':
        if user_soc_team:
            alerts = alerts.filter(assigned_team=user_soc_team)
        else:
            alerts = alerts.none()
    elif team_param and team_param.isdigit():
        alerts = alerts.filter(assigned_team_id=int(team_param))
    elif team_param in ('L1', 'L2', 'L3', 'ENG', 'MGMT'):
        alerts = alerts.filter(assigned_team__tier=team_param)

    now = timezone.now()
    month = request.GET.get('month')
    year = request.GET.get('year')

    # Date filtering: support 'all' and default to 'all' so active alerts aren't hidden
    if month and month != 'all' and year and year != 'all':
        try:
            m, y = int(month), int(year)
            alerts = alerts.filter(alert_time__year=y, alert_time__month=m)
            selected_month = m
            selected_year = y
        except (ValueError, TypeError):
            selected_month = 'all'
            selected_year = 'all'
    elif month and month != 'all':
        try:
            m = int(month)
            alerts = alerts.filter(alert_time__month=m)
            selected_month = m
            selected_year = 'all'
        except (ValueError, TypeError):
            selected_month = 'all'
            selected_year = 'all'
    elif year and year != 'all':
        try:
            y = int(year)
            alerts = alerts.filter(alert_time__year=y)
            selected_month = 'all'
            selected_year = y
        except (ValueError, TypeError):
            selected_month = 'all'
            selected_year = 'all'
    else:
        selected_month = 'all'
        selected_year = 'all'

    search = request.GET.get('search')
    if search:
        alerts = alerts.filter(
            Q(alert_name__icontains=search) |
            Q(hostname__icontains=search) |
            Q(username__icontains=search)
        )

    severity_summary = alerts.aggregate(
        total=Count('id'),
        critical=Count('id', filter=Q(severity__iexact='critical')),
        high=Count('id', filter=Q(severity__iexact='high')),
        medium=Count('id', filter=Q(severity__iexact='medium')),
        low=Count('id', filter=Q(severity__iexact='low')),
    )

    soc_teams = SocTeam.objects.filter(is_active=True).order_by('tier', 'name')
    context = {
        'new_alerts': alerts.filter(status='New'),
        'in_progress_alerts': alerts.filter(status='In Progress'),
        'awaiting_alerts': alerts.filter(status='Awaiting Action'),
        'pending_alerts': alerts.filter(status='Pending'),
        'escalated_alerts': alerts.filter(status__startswith='Escalated'),
        'remediation_alerts': alerts.filter(status='Remediation'),
        'true_positives': alerts.filter(verdict='True Positive', status='Closed'),
        'false_positives': alerts.filter(verdict='False Positive', status='Closed'),
        'closed_other_alerts': alerts.filter(status='Closed').exclude(verdict__in=['True Positive', 'False Positive']),
        'closed_alerts': alerts.filter(status='Closed'),
        'archived_alerts': alerts.filter(status='Archived'),
        'users': User.objects.filter(is_active=True),
        'soc_teams': soc_teams,
        'user_soc_team': user_soc_team,
        'selected_team': team_param,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'severity_summary': severity_summary,
        'months': [
            ('all', 'All Months'),
            (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
            (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
            (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December'),
        ],
        'years': ['all', 2024, 2025, 2026, 2027, 2028],
    }
    return render(request, 'ariba_soc/alert_board.html', context)


@login_required
@permission_required('can_view_alerts')
def alert_detail(request, alert_id):
    alert = get_object_or_404(
        Alert.objects.select_related('assignee', 'source', 'assigned_by', 'assigned_team'), id=alert_id,
    )
    comments = alert.comments.select_related('user').all()
    audit_logs = alert.audit_logs.select_related('user').all()[:50]
    transitions = alert.transitions.select_related('actor').all()[:50]
    escalation_records = alert.escalation_records.all()[:10]
    form = AlertEditForm(instance=alert, user=request.user)
    soc_teams = SocTeam.objects.filter(is_active=True).order_by('tier', 'name')
    is_bookmarked = AlertBookmark.objects.filter(user=request.user, alert=alert).exists()
    is_watching = AlertWatcher.objects.filter(user=request.user, alert=alert).exists()
    attachments = alert.attachments.select_related('uploaded_by').all()
    watchers = alert.watchers.select_related('user').all()
    related_alerts = find_related_alerts(alert)
    from settings_manager.models import Playbook
    playbooks = Playbook.for_alert(alert)
    fp_reports = alert.fp_reports.select_related('reported_by').all()[:10]
    return render(request, 'ariba_soc/alert_detail.html', {
        'alert': alert, 'comments': comments, 'audit_logs': audit_logs,
        'transitions': transitions, 'escalation_records': escalation_records,
        'form': form, 'users': User.objects.filter(is_active=True),
        'soc_teams': soc_teams, 'is_bookmarked': is_bookmarked,
        'is_watching': is_watching, 'attachments': attachments, 'watchers': watchers,
        'related_alerts': related_alerts,
        'merged_children': alert.merged_children.all(),
        'playbooks': playbooks,
        'fp_reports': fp_reports,
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
def alert_enrich(request, alert_id):
    alert = get_object_or_404(Alert, id=alert_id)
    from wazuh_integration.enrichment_service import EnrichmentService
    result = EnrichmentService.enrich_alert(alert)
    alert.save(update_fields=[
        'enrichment_data', 'enrichment_status',
        'enrichment_updated_at', 'enrichment_error',
    ])
    create_audit_log(alert, request.user, 'Enriched', '', f"Enrichment {result['status']}", request)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': result['status'], 'providers': result['providers']})
    messages.success(request, f"Enrichment {result['status'].lower()}.")
    return redirect('alerts:detail', alert_id=alert.id)


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
        comment.comment_type = form.cleaned_data.get('comment_type') or 'Analyst Note'
        comment.save()
        mention_usernames = set(re.findall(r'@([A-Za-z0-9_.@+-]+)', comment.comment or ''))
        mentioned = list(User.objects.filter(username__in=mention_usernames, is_active=True))
        for u in mentioned:
            if u != request.user:
                AlertWatcher.objects.get_or_create(
                    alert=alert, user=u, defaults={'added_by': request.user},
                )
                Notification.objects.create(
                    user=u,
                    message=f"{request.user.username} mentioned you on alert #{alert.id}",
                    link=reverse('alerts:detail', args=[alert.id]),
                )
        for w in alert.watchers.exclude(user=request.user).select_related('user'):
            Notification.objects.create(
                user=w.user,
                message=f"New comment on alert #{alert.id}: {alert.alert_name[:80]}",
                link=reverse('alerts:detail', args=[alert.id]),
            )
        audit_note = form.cleaned_data['comment'][:200]
        if mentioned:
            audit_note = f"{audit_note} (mentions: {', '.join(u.username for u in mentioned)})"
        create_audit_log(alert, request.user, 'Comment Added', '', audit_note, request)
        messages.success(request, 'Comment added.')
    return redirect('alerts:detail', alert_id=alert_id)


# ---------------------------------------------------------------------------
# Workflow endpoints
# ---------------------------------------------------------------------------

@login_required
@require_POST
def alert_claim(request, alert_id):
    version = int(request.POST.get('workflow_version', 1))
    try:
        alert = workflow.claim_alert(alert_id, request.user, version, request=request)
        messages.success(request, 'Alert claimed and investigation started.')
    except workflow.WorkflowError as exc:
        return _handle_workflow_error(request, exc, alert_id)
    return redirect('alerts:detail', alert_id=alert.id)


@login_required
@require_POST
def alert_escalate(request, alert_id):
    version = int(request.POST.get('workflow_version', 1))
    reason = request.POST.get('escalation_reason', '').strip()
    tier = request.POST.get('tier', 'L2').upper()
    try:
        alert = workflow.escalate_alert(alert_id, request.user, tier, reason, version, request=request)
        messages.success(request, f'Alert escalated to {tier}.')
    except workflow.WorkflowError as exc:
        return _handle_workflow_error(request, exc, alert_id)
    return redirect('alerts:detail', alert_id=alert.id)


@login_required
@require_POST
def alert_escalation_accept(request, alert_id):
    version = int(request.POST.get('workflow_version', 1))
    try:
        alert = workflow.accept_escalation(alert_id, request.user, version, request=request)
        messages.success(request, 'Escalation accepted.')
    except workflow.WorkflowError as exc:
        return _handle_workflow_error(request, exc, alert_id)
    return redirect('alerts:detail', alert_id=alert.id)


@login_required
@require_POST
def alert_escalation_return(request, alert_id):
    version = int(request.POST.get('workflow_version', 1))
    reason = request.POST.get('return_reason', '').strip()
    try:
        alert = workflow.return_escalation(alert_id, request.user, reason, version, request=request)
        messages.success(request, f'Alert returned to {alert.escalated_from_tier or "L1"}.')
    except workflow.WorkflowError as exc:
        return _handle_workflow_error(request, exc, alert_id)
    return redirect('alerts:detail', alert_id=alert.id)


@login_required
@require_POST
def alert_resolve(request, alert_id):
    version = int(request.POST.get('workflow_version', 1))
    resolution = request.POST.get('resolution', '').strip()
    try:
        alert = workflow.resolve_alert(alert_id, request.user, resolution, version, request=request)
        messages.success(request, 'Alert resolved.')
    except workflow.WorkflowError as exc:
        return _handle_workflow_error(request, exc, alert_id)
    return redirect('alerts:detail', alert_id=alert.id)


@login_required
@require_POST
def alert_close(request, alert_id):
    version = int(request.POST.get('workflow_version', 1))
    verdict = request.POST.get('verdict', '').strip()
    closure_reason = request.POST.get('closure_comment', '').strip()
    if not verdict or verdict == 'None':
        messages.error(request, 'Verdict must be set before closing.')
        return redirect('alerts:detail', alert_id=alert_id)
    if not closure_reason:
        messages.error(request, 'Closure comment is required.')
        return redirect('alerts:detail', alert_id=alert_id)
    try:
        alert = workflow.close_alert(alert_id, request.user, verdict, closure_reason, version, request=request)
        messages.success(request, 'Alert closed.')
    except workflow.WorkflowError as exc:
        return _handle_workflow_error(request, exc, alert_id)
    return redirect('alerts:detail', alert_id=alert.id)


@login_required
@require_POST
def alert_reopen(request, alert_id):
    version = int(request.POST.get('workflow_version', 1))
    reason = request.POST.get('reopen_reason', 'Reopened by analyst').strip()
    try:
        alert = workflow.reopen_alert(alert_id, request.user, reason, version, request=request)
        messages.success(request, 'Alert reopened.')
    except workflow.WorkflowError as exc:
        return _handle_workflow_error(request, exc, alert_id)
    return redirect('alerts:detail', alert_id=alert.id)


@login_required
@require_POST
def alert_create_incident(request, alert_id):
    version = int(request.POST.get('workflow_version', 1))
    reason = request.POST.get('incident_reason', '').strip()
    if not reason:
        messages.error(request, 'Incident reason is required.')
        return redirect('alerts:detail', alert_id=alert_id)
    try:
        alert = workflow.create_incident(alert_id, request.user, reason, version, request=request)
        messages.success(request, 'Incident created.')
    except workflow.WorkflowError as exc:
        return _handle_workflow_error(request, exc, alert_id)
    return redirect('alerts:detail', alert_id=alert_id)


# ---------------------------------------------------------------------------
# Legacy / compatibility endpoints (kept for backward compat)
# ---------------------------------------------------------------------------

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
@permission_required('can_view_alerts')
def my_alerts(request):
    alerts = Alert.objects.filter(assignee=request.user).select_related('source')
    if not alerts.exists():
        return render(request, 'ariba_soc/my_alerts.html', {'alerts': alerts, 'no_alerts': True, 'users': User.objects.filter(is_active=True)})
    paginator = Paginator(alerts, 50)
    page = request.GET.get('page', 1)
    alerts_page = paginator.get_page(page)
    return render(request, 'ariba_soc/my_alerts.html', {'alerts': alerts_page, 'users': User.objects.filter(is_active=True)})


@login_required
@permission_required('can_view_alerts')
def alerts_api(request):
    data = list(Alert.objects.select_related('assignee').only(
        'id', 'alert_name', 'severity', 'status', 'verdict', 'priority',
        'assignee_id', 'source_name', 'hostname', 'alert_time', 'rule_id', 'sla_status',
        'workflow_state', 'current_tier', 'workflow_version',
    ).order_by('-alert_time')[:100].values(
        'id', 'alert_name', 'severity', 'status', 'verdict', 'priority',
        'assignee__username', 'source_name', 'hostname', 'alert_time', 'rule_id', 'sla_status',
        'workflow_state', 'current_tier', 'workflow_version',
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

    with transaction.atomic():
        if action == 'assign':
            check_perm(request.user, 'can_assign_others')
            user_id = value
            if user_id:
                assignee = get_object_or_404(User, id=user_id)
                for alert in alerts:
                    assign_alert(alert, request.user, assignee, request)
            messages.success(request, f'{count} alerts assigned.')
        elif action == 'assign_team':
            team_id = value
            if team_id:
                target_team = get_object_or_404(SocTeam, id=team_id)
                for alert in alerts:
                    old_val = alert.assigned_team.name if alert.assigned_team else 'Unassigned'
                    alert.assigned_team = target_team
                    alert.current_owner_team = target_team.tier
                    alert.save(update_fields=['assigned_team', 'current_owner_team'])
                    create_audit_log(alert, request.user, 'Team Reassigned', old_val, target_team.name, request)
                messages.success(request, f'{count} alerts assigned to team {target_team.name}.')
        elif action == 'status':
            check_perm(request.user, 'can_change_status')
            allowed_statuses = list(StatusSettings.objects.filter(is_active=True).values_list('name', flat=True))
            if value not in allowed_statuses:
                messages.error(request, f'Invalid status: {value}')
                return redirect('alerts:table')
            old_val = ', '.join(alerts.values_list('status', flat=True).distinct())
            alerts.update(status=value)
            for alert in alerts:
                create_audit_log(alert, request.user, 'Status Changed', old_val, value, request)
            messages.success(request, f'{count} alerts status changed to {value}.')
        elif action == 'verdict':
            check_perm(request.user, 'can_change_verdict')
            allowed_verdicts = list(VerdictSettings.objects.filter(is_active=True).values_list('name', flat=True))
            if value not in allowed_verdicts:
                messages.error(request, f'Invalid verdict: {value}')
                return redirect('alerts:table')
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
@permission_required('can_change_status')
def alert_move_api(request, alert_id):
    alert = get_object_or_404(Alert, id=alert_id)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid JSON body'}, status=400)

    new_status = data.get('status')
    new_verdict = data.get('verdict')

    allowed_statuses = list(StatusSettings.objects.filter(is_active=True).values_list('name', flat=True))
    allowed_verdicts = list(VerdictSettings.objects.filter(is_active=True).values_list('name', flat=True))

    status_changed = False
    verdict_changed = False

    if new_status and new_status in allowed_statuses:
        if alert.status != new_status:
            old_status = alert.status
            alert.status = new_status
            status_changed = True
            if new_status == 'In Progress':
                alert.acknowledged_at = alert.acknowledged_at or timezone.now()
            elif new_status == 'Closed':
                alert.closed_at = alert.closed_at or timezone.now()
                alert.closed_by = request.user
            create_audit_log(alert, request.user, 'Status Changed', old_status, new_status, request)

    if new_verdict and new_verdict in allowed_verdicts:
        if alert.verdict != new_verdict:
            old_verdict = alert.verdict
            alert.verdict = new_verdict
            verdict_changed = True
            create_audit_log(alert, request.user, 'Verdict Changed', old_verdict, new_verdict, request)

    if status_changed or verdict_changed:
        alert.save()
        return JsonResponse({'success': True, 'status': alert.status, 'verdict': alert.verdict})

    if new_status and new_status not in allowed_statuses:
        return JsonResponse({'success': False, 'error': f'Invalid status: {new_status}'}, status=400)

    return JsonResponse({'success': True, 'status': alert.status, 'verdict': alert.verdict})


# ---------------------------------------------------------------------------
# Phase 5: Asset Inventory Views
# ---------------------------------------------------------------------------
from .models import Asset
from .forms import AssetForm
from .services import sync_assets_from_wazuh, recalculate_alerts_risk_score


@login_required
def asset_directory(request):
    """
    Asset Inventory and Criticality Directory with filtering, search, and live metrics.
    """
    qs = Asset.objects.all()
    search = request.GET.get('search', '').strip()
    criticality = request.GET.get('criticality', '').strip()
    environment = request.GET.get('environment', '').strip()
    asset_type = request.GET.get('asset_type', '').strip()

    if search:
        qs = qs.filter(
            Q(hostname__icontains=search) |
            Q(name__icontains=search) |
            Q(ip_address__icontains=search) |
            Q(agent_id__icontains=search) |
            Q(business_unit__icontains=search) |
            Q(owner__icontains=search)
        )

    if criticality:
        qs = qs.filter(criticality=criticality)
    if environment:
        qs = qs.filter(environment=environment)
    if asset_type:
        qs = qs.filter(asset_type=asset_type)

    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    stats = {
        'total': Asset.objects.count(),
        'critical': Asset.objects.filter(criticality='CRITICAL').count(),
        'high': Asset.objects.filter(criticality='HIGH').count(),
        'medium': Asset.objects.filter(criticality='MEDIUM').count(),
        'low': Asset.objects.filter(criticality='LOW').count(),
        'auto_discovered': Asset.objects.filter(auto_discovered=True).count(),
    }

    form = AssetForm()

    return render(request, 'ariba_soc/asset_directory.html', {
        'page_obj': page_obj,
        'assets': page_obj,
        'stats': stats,
        'form': form,
        'search': search,
        'criticality': criticality,
        'environment': environment,
        'asset_type': asset_type,
    })


@login_required
@require_POST
def asset_create(request):
    form = AssetForm(request.POST)
    if form.is_valid():
        asset = form.save()
        messages.success(request, f'Asset "{asset.name or asset.hostname}" created successfully.')
    else:
        errors = '; '.join([f"{f}: {e[0]}" for f, e in form.errors.items()])
        messages.error(request, f'Failed to create asset: {errors}')
    return redirect('alerts:assets_list')


@login_required
def asset_edit(request, asset_id):
    asset = get_object_or_404(Asset, id=asset_id)
    if request.method == 'POST':
        form = AssetForm(request.POST, instance=asset)
        if form.is_valid():
            asset = form.save(commit=False)
            asset.save(recalc_multiplier=True)
            form.save_m2m()
            messages.success(request, f'Asset "{asset.name or asset.hostname}" updated.')
            return redirect('alerts:assets_list')
        else:
            errors = '; '.join([f"{f}: {e[0]}" for f, e in form.errors.items()])
            messages.error(request, f'Failed to update asset: {errors}')
            return redirect('alerts:assets_list')

    return JsonResponse({
        'id': asset.id,
        'name': asset.name,
        'hostname': asset.hostname,
        'ip_address': asset.ip_address or '',
        'agent_id': asset.agent_id or '',
        'criticality': asset.criticality,
        'criticality_multiplier': asset.criticality_multiplier,
        'asset_type': asset.asset_type,
        'environment': asset.environment,
        'business_unit': asset.business_unit,
        'owner': asset.owner,
        'mac_address': asset.mac_address,
        'os_name': asset.os_name,
        'description': asset.description,
        'is_active': asset.is_active,
    })


@login_required
@require_POST
def asset_delete(request, asset_id):
    asset = get_object_or_404(Asset, id=asset_id)
    name = asset.name or asset.hostname
    asset.delete()
    messages.success(request, f'Asset "{name}" deleted.')
    return redirect('alerts:assets_list')


@login_required
@require_POST
def asset_sync_wazuh(request):
    try:
        res = sync_assets_from_wazuh()
        if 'error' in res:
            messages.error(request, f"Wazuh Sync error: {res['error']}")
        else:
            messages.success(request, f"Wazuh Asset Discovery complete: {res['total']} agents scanned, {res['created']} added, {res['updated']} updated.")
    except Exception as e:
        messages.error(request, f"Failed to sync from Wazuh: {str(e)}")
    return redirect('alerts:assets_list')


@login_required
@require_POST
def recalculate_all_alerts_risk(request):
    try:
        count = recalculate_alerts_risk_score()
        messages.success(request, f"Recalculated dynamic risk score and asset links for {count} alerts.")
    except Exception as e:
        messages.error(request, f"Failed to recalculate risk scores: {str(e)}")
    return redirect('alerts:assets_list')


# ---------------------------------------------------------------------------
# Phase 6: Saved filters, tags/bookmarks, CSV export, single-alert PDF
# ---------------------------------------------------------------------------

@login_required
@permission_required('can_view_alerts')
def alert_export_csv(request):
    import csv
    alerts, _, _, _ = _apply_alert_filters(request)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="alerts_export.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Wazuh ID', 'Time', 'Name', 'Severity', 'Status', 'Verdict',
        'Assignee', 'Team', 'Source IP', 'Destination IP', 'Hostname',
        'Agent', 'Rule ID', 'MITRE Tactic', 'Tags', 'Risk Score', 'SLA Status',
    ])
    for a in alerts[:5000]:
        writer.writerow([
            a.id, a.wazuh_alert_id, a.alert_time.isoformat() if a.alert_time else '',
            a.alert_name, a.severity, a.status, a.verdict,
            a.assignee.username if a.assignee else '',
            a.assigned_team.name if a.assigned_team else '',
            a.source_ip, a.destination_ip, a.hostname, a.agent_name, a.rule_id,
            a.mitre_tactic, '; '.join(a.tags or []), a.risk_score, a.sla_status,
        ])
    return response


@login_required
@permission_required('can_view_alerts')
def alert_export_pdf(request):
    """Export filtered alerts into an executive Ariba SOC PDF report."""
    import io
    from xml.sax.saxutils import escape
    from django.utils import timezone
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

    alerts, filters, _, _ = _apply_alert_filters(request)
    total_count = alerts.count()
    limit = 500
    export_alerts = list(alerts[:limit])

    downloaded_by = request.user.get_full_name() or request.user.username
    if request.user.email and request.user.email != downloaded_by:
        downloaded_by_display = f"{downloaded_by} ({request.user.email})"
    else:
        downloaded_by_display = downloaded_by

    download_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        title='Ariba SOC - Alerts Telemetry Report',
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'AribaExpTitle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a'),
        alignment=0,
    )
    subtitle_style = ParagraphStyle(
        'AribaExpSub',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#2563eb'),
    )
    meta_style = ParagraphStyle(
        'AribaExpMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#334155'),
    )

    story = [
        Paragraph('ARIBA SOC', title_style),
        Paragraph('SECURITY OPERATIONS CENTER &mdash; ALERTS TELEMETRY EXPORT REPORT', subtitle_style),
        Spacer(1, 3),
        HRFlowable(width='100%', thickness=1.5, color=colors.HexColor('#2563eb'), spaceAfter=6, spaceBefore=2),
    ]

    sev_counts = {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0, 'Informational': 0}
    for a in export_alerts:
        sev_counts[a.severity] = sev_counts.get(a.severity, 0) + 1

    meta_rows = [
        [
            Paragraph('<b>System:</b> Ariba SOC (Enterprise SIEM/SOAR)', meta_style),
            Paragraph(f'<b>Downloaded By:</b> {escape(downloaded_by_display)}', meta_style),
            Paragraph(f'<b>Exported Alerts:</b> {len(export_alerts)} (of {total_count} total)', meta_style),
        ],
        [
            Paragraph('<b>Classification:</b> CONFIDENTIAL // TLP:AMBER', meta_style),
            Paragraph(f'<b>Downloaded On:</b> {download_time}', meta_style),
            Paragraph(f'<b>Severity Breakdown:</b> Crit: {sev_counts.get("Critical", 0)} | High: {sev_counts.get("High", 0)} | Med: {sev_counts.get("Medium", 0)} | Low: {sev_counts.get("Low", 0)}', meta_style),
        ],
    ]
    meta_table = Table(meta_rows, colWidths=[80 * mm, 100 * mm, 89 * mm])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8))

    table_headers = ['ID', 'Alert Time', 'Severity', 'Status', 'Alert Name / Description', 'Agent / Host', 'Rule ID', 'Events']
    table_data = [table_headers]

    for a in export_alerts:
        t_str = a.alert_time.strftime('%Y-%m-%d %H:%M') if a.alert_time else '—'
        name_short = (a.alert_name[:55] + '...') if len(a.alert_name or '') > 55 else (a.alert_name or '—')
        host_agent = a.agent_name or a.hostname or '—'
        table_data.append([
            str(a.id),
            t_str,
            str(a.severity),
            str(a.status),
            name_short,
            host_agent,
            str(a.rule_id or '—'),
            str(a.event_count),
        ])

    table = Table(table_data, colWidths=[14 * mm, 30 * mm, 22 * mm, 24 * mm, 105 * mm, 34 * mm, 22 * mm, 18 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(table)

    def draw_landscape_decorations(canvas, d):
        canvas.saveState()
        width, height = landscape(A4)
        canvas.setFont('Helvetica-Bold', 8)
        canvas.setFillColor(colors.HexColor('#1e40af'))
        canvas.drawString(14 * mm, height - 10 * mm, 'ARIBA SOC')
        canvas.setFont('Helvetica', 7.5)
        canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawRightString(width - 14 * mm, height - 10 * mm, 'Alerts Telemetry Report')
        canvas.setStrokeColor(colors.HexColor('#e2e8f0'))
        canvas.setLineWidth(0.6)
        canvas.line(14 * mm, height - 12 * mm, width - 14 * mm, height - 12 * mm)

        canvas.line(14 * mm, 12 * mm, width - 14 * mm, 12 * mm)
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawString(14 * mm, 8 * mm, f'Ariba SOC Confidential — Downloaded by {downloaded_by} on {download_time}')
        canvas.drawRightString(width - 14 * mm, 8 * mm, f'Page {canvas.getPageNumber()}')
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_landscape_decorations, onLaterPages=draw_landscape_decorations)
    pdf = buf.getvalue()
    buf.close()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Ariba_SOC_Alerts_Export.pdf"'
    return response


@login_required
@permission_required('can_view_alerts')
def alert_pdf(request, alert_id):
    """Generate a high-fidelity single alert PDF dossier with Ariba SOC branding, downloader, and timestamp."""
    import io
    from xml.sax.saxutils import escape
    from django.utils import timezone
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

    alert = get_object_or_404(
        Alert.objects.select_related('assignee', 'source', 'assigned_team'), id=alert_id,
    )

    downloaded_by = request.user.get_full_name() or request.user.username
    if request.user.email and request.user.email != downloaded_by:
        downloaded_by_display = f"{downloaded_by} ({request.user.email})"
    else:
        downloaded_by_display = downloaded_by

    download_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        title=f'Ariba SOC - Alert #{alert.id}',
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'AribaHeaderTitle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        alignment=0,
    )
    subtitle_style = ParagraphStyle(
        'AribaHeaderSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#2563eb'),
    )
    meta_label_style = ParagraphStyle(
        'AribaMetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#475569'),
    )
    meta_val_style = ParagraphStyle(
        'AribaMetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#0f172a'),
    )
    section_style = ParagraphStyle(
        'AribaSection',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=8,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        'AribaBody',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#334155'),
    )

    story = [
        Paragraph('ARIBA SOC', title_style),
        Paragraph('SECURITY OPERATIONS CENTER &mdash; INCIDENT INVESTIGATION REPORT', subtitle_style),
        Spacer(1, 4),
        HRFlowable(width='100%', thickness=1.5, color=colors.HexColor('#2563eb'), spaceAfter=8, spaceBefore=2),
    ]

    meta_box_data = [
        [
            Paragraph('<b>System:</b> Ariba SOC (Enterprise SIEM/SOAR)', meta_label_style),
            Paragraph(f'<b>Downloaded By:</b> {escape(downloaded_by_display)}', meta_val_style),
        ],
        [
            Paragraph('<b>Classification:</b> CONFIDENTIAL // TLP:AMBER', meta_label_style),
            Paragraph(f'<b>Downloaded On:</b> {download_time}', meta_val_style),
        ],
    ]
    meta_box = Table(meta_box_data, colWidths=[85 * mm, 93 * mm])
    meta_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_box)
    story.append(Spacer(1, 10))

    story.append(Paragraph(f'<b>Alert #{alert.id}:</b> {escape(alert.alert_name or "Unknown Alert")}', section_style))
    story.append(Spacer(1, 4))

    rows = [
        ['Field', 'Value'],
        ['Wazuh Alert ID', str(alert.wazuh_alert_id or alert.id)],
        ['Alert Event Time', alert.alert_time.strftime('%Y-%m-%d %H:%M:%S') if alert.alert_time else '—'],
        ['Severity Level', str(alert.severity)],
        ['Investigation Status', str(alert.status)],
        ['Triage Verdict', str(alert.verdict or 'Unassigned')],
        ['Priority', str(alert.priority)],
        ['Assigned Analyst', alert.assignee.get_full_name() or alert.assignee.username if alert.assignee else 'Unassigned'],
        ['Assigned SOC Team', alert.assigned_team.name if alert.assigned_team else '—'],
        ['Source IP', alert.source_ip or '—'],
        ['Destination IP', alert.destination_ip or '—'],
        ['Host / Endpoint', alert.hostname or '—'],
        ['Agent Name', f"{alert.agent_name} (ID: {alert.agent_id})" if alert.agent_id else (alert.agent_name or '—')],
        ['Wazuh Rule ID', alert.rule_id or '—'],
        ['Aggregated Events', str(alert.event_count)],
        ['MITRE ATT&CK Tactic', alert.mitre_tactic or '—'],
        ['MITRE ATT&CK Technique', alert.mitre_technique or '—'],
        ['Tags / Indicators', ', '.join(alert.tags or []) or '—'],
        ['Risk Score', str(alert.risk_score)],
        ['SLA Status', str(alert.sla_status)],
        ['SLA Deadline', alert.sla_due_at.strftime('%Y-%m-%d %H:%M') if alert.sla_due_at else '—'],
        ['Enrichment Status', alert.get_enrichment_status_display()],
    ]

    sev_colors = {
        'Critical': '#b91c1c',
        'High': '#c2410c',
        'Medium': '#a16207',
        'Low': '#1d4ed8',
        'Informational': '#475569',
    }
    header_color = colors.HexColor(sev_colors.get(alert.severity, '#1e293b'))

    table = Table(rows, colWidths=[48 * mm, 130 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(table)

    for label, body in (
        ('Alert Log & Raw Telemetry', alert.full_log),
        ('Analyst Investigation Comments', alert.analyst_comment),
        ('Remediation & Containment Actions', alert.remediation_note),
        ('Root Cause Summary', alert.root_cause_summary),
    ):
        if body:
            story.append(Spacer(1, 8))
            story.append(Paragraph(f'<b>{label}</b>', section_style))
            story.append(Paragraph(escape(str(body)).replace('\n', '<br/>'), body_style))

    def draw_page_decorations(canvas, d):
        canvas.saveState()
        width, height = A4
        canvas.setFont('Helvetica-Bold', 8)
        canvas.setFillColor(colors.HexColor('#1e40af'))
        canvas.drawString(16 * mm, height - 12 * mm, 'ARIBA SOC')
        canvas.setFont('Helvetica', 7.5)
        canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawRightString(width - 16 * mm, height - 12 * mm, f'Alert #{alert.id} Investigation Dossier')
        canvas.setStrokeColor(colors.HexColor('#e2e8f0'))
        canvas.setLineWidth(0.6)
        canvas.line(16 * mm, height - 14 * mm, width - 16 * mm, height - 14 * mm)

        canvas.line(16 * mm, 14 * mm, width - 16 * mm, 14 * mm)
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawString(16 * mm, 9 * mm, f'Ariba SOC Confidential — Downloaded by {downloaded_by} on {download_time}')
        canvas.drawRightString(width - 16 * mm, 9 * mm, f'Page {canvas.getPageNumber()}')
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_page_decorations, onLaterPages=draw_page_decorations)
    pdf = buf.getvalue()
    buf.close()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Ariba_SOC_Alert_{alert.id}.pdf"'
    return response


@login_required
@require_POST
def alert_toggle_bookmark(request, alert_id):
    alert = get_object_or_404(Alert, id=alert_id)
    bm, created = AlertBookmark.objects.get_or_create(user=request.user, alert=alert)
    if not created:
        bm.delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'is_bookmarked': created})
    return redirect(request.META.get('HTTP_REFERER', 'alerts:table'))


@login_required
@require_POST
def alert_set_tags(request, alert_id):
    alert = get_object_or_404(Alert, id=alert_id)
    raw = request.POST.get('tags', '')
    tags = []
    for t in raw.split(','):
        t = t.strip()[:50]
        if t and t not in tags:
            tags.append(t)
    old = alert.tags or []
    alert.tags = tags
    alert.save(update_fields=['tags'])
    create_audit_log(alert, request.user, 'Tags Updated', ', '.join(old), ', '.join(tags), request)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'tags': tags})
    messages.success(request, 'Tags updated.')
    return redirect('alerts:detail', alert_id=alert.id)


@login_required
@require_POST
def saved_filter_save(request):
    name = (request.POST.get('name') or '').strip()[:120]
    query = (request.POST.get('query') or '').strip()[:2000]
    is_shared = request.POST.get('is_shared') in ('1', 'on', 'true')
    if not name:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Name required'}, status=400)
        messages.error(request, 'Filter name is required.')
        return redirect('alerts:table')
    sf, _ = SavedFilter.objects.update_or_create(
        user=request.user, name=name,
        defaults={'query': query, 'is_shared': is_shared},
    )
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'id': sf.id, 'name': sf.name, 'is_shared': sf.is_shared})
    messages.success(request, f'Filter "{name}" saved.')
    return redirect('alerts:table')


@login_required
@require_POST
def saved_filter_delete(request, pk):
    sf = get_object_or_404(SavedFilter, id=pk)
    if sf.user_id != request.user.id and not request.user.is_superuser:
        raise PermissionDenied('Not your saved filter.')
    sf.delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'deleted': True})
    messages.success(request, 'Saved filter deleted.')
    return redirect('alerts:table')


# ---------------------------------------------------------------------------
# Phase 7: evidence attachments + @mentions/watchers
# ---------------------------------------------------------------------------

ALLOWED_ATTACHMENT_EXT = {
    '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg', '.pdf',
    '.txt', '.log', '.csv', '.json', '.xml', '.pcap', '.evtx', '.doc',
    '.docx', '.xls', '.xlsx', '.zip', '.gz', '.eml',
}
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024


def _notify_watchers(alert, actor, message):
    for w in alert.watchers.exclude(user=actor).select_related('user'):
        Notification.objects.create(
            user=w.user, message=message,
            link=reverse('alerts:detail', args=[alert.id]),
        )


@login_required
@require_POST
def alert_attachment_upload(request, alert_id):
    alert = get_object_or_404(Alert, id=alert_id)
    upload = request.FILES.get('file')
    if not upload:
        messages.error(request, 'No file selected.')
        return redirect('alerts:detail', alert_id=alert.id)
    ext = os.path.splitext(upload.name)[1].lower()
    if ext not in ALLOWED_ATTACHMENT_EXT:
        messages.error(request, f'File type "{ext or "unknown"}" is not allowed.')
        return redirect('alerts:detail', alert_id=alert.id)
    if upload.size > MAX_ATTACHMENT_BYTES:
        messages.error(request, 'File exceeds the 25 MB limit.')
        return redirect('alerts:detail', alert_id=alert.id)
    attachment = AlertAttachment.objects.create(
        alert=alert,
        file=upload,
        original_name=upload.name[:255],
        description=(request.POST.get('description') or '')[:255],
        uploaded_by=request.user,
    )
    create_audit_log(alert, request.user, 'Evidence Attached', '', attachment.original_name, request)
    _notify_watchers(alert, request.user, f"New evidence on alert #{alert.id}: {attachment.original_name}")
    messages.success(request, 'Evidence uploaded.')
    return redirect('alerts:detail', alert_id=alert.id)


@login_required
def alert_attachment_download(request, pk):
    attachment = get_object_or_404(AlertAttachment, id=pk)
    try:
        return FileResponse(
            attachment.file.open('rb'), as_attachment=True,
            filename=attachment.original_name or os.path.basename(attachment.file.name),
        )
    except (FileNotFoundError, ValueError):
        messages.error(request, 'Attachment file is missing.')
        return redirect('alerts:detail', alert_id=attachment.alert_id)


@login_required
@require_POST
def alert_attachment_delete(request, pk):
    attachment = get_object_or_404(AlertAttachment, id=pk)
    alert = attachment.alert
    if attachment.uploaded_by_id != request.user.id and not request.user.is_superuser:
        raise PermissionDenied('You cannot delete this attachment.')
    name = attachment.original_name
    attachment.file.delete(save=False)
    attachment.delete()
    create_audit_log(alert, request.user, 'Evidence Removed', name, '', request)
    messages.success(request, 'Evidence removed.')
    return redirect('alerts:detail', alert_id=alert.id)


@login_required
@require_POST
def alert_watcher_toggle(request, alert_id):
    alert = get_object_or_404(Alert, id=alert_id)
    watcher, created = AlertWatcher.objects.get_or_create(
        alert=alert, user=request.user, defaults={'added_by': request.user},
    )
    if not created:
        watcher.delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'is_watching': created})
    messages.success(request, 'Watching alert.' if created else 'Stopped watching alert.')
    return redirect('alerts:detail', alert_id=alert.id)


@login_required
@require_POST
def alert_watcher_add(request, alert_id):
    alert = get_object_or_404(Alert, id=alert_id)
    user_id = request.POST.get('user_id')
    user = get_object_or_404(User, id=user_id)
    AlertWatcher.objects.get_or_create(alert=alert, user=user, defaults={'added_by': request.user})
    create_audit_log(alert, request.user, 'Watcher Added', '', user.username, request)
    Notification.objects.create(
        user=user, message=f"{request.user.username} added you as a watcher on alert #{alert.id}",
        link=reverse('alerts:detail', args=[alert.id]),
    )
    messages.success(request, f'{user.username} added as watcher.')
    return redirect('alerts:detail', alert_id=alert.id)


@login_required
@require_POST
def alert_watcher_remove(request, alert_id, user_id):
    alert = get_object_or_404(Alert, id=alert_id)
    AlertWatcher.objects.filter(alert=alert, user_id=user_id).delete()
    messages.success(request, 'Watcher removed.')
    return redirect('alerts:detail', alert_id=alert.id)


@login_required
def alert_related(request, alert_id):
    """JSON list of alerts that correlate with the given alert."""
    alert = get_object_or_404(Alert, id=alert_id)
    related = find_related_alerts(alert)
    data = [
        {
            'id': a.id,
            'name': a.alert_name,
            'severity': a.severity,
            'status': a.status,
            'rule_id': a.rule_id,
            'source_ip': a.source_ip,
            'alert_time': a.alert_time.isoformat() if a.alert_time else '',
            'relation_score': getattr(a, 'relation_score', 0),
            'url': reverse('alerts:detail', args=[a.id]),
        }
        for a in related
    ]
    return JsonResponse({'related': data})


@login_required
@permission_required('can_change_status')
@require_POST
def alert_merge(request, alert_id):
    primary = get_object_or_404(Alert, id=alert_id)
    ids = request.POST.getlist('merge_ids')
    if not ids:
        messages.error(request, 'Select at least one alert to merge.')
        return redirect('alerts:detail', alert_id=primary.id)
    duplicates = list(Alert.objects.filter(id__in=ids).exclude(id=primary.id))
    merged = merge_alerts(primary, duplicates, request.user, request)
    if merged:
        messages.success(request, f'Merged {len(merged)} alert(s) into this one.')
    else:
        messages.info(request, 'Nothing to merge.')
    return redirect('alerts:detail', alert_id=primary.id)


@login_required
@permission_required('can_change_status')
@require_POST
def alert_unmerge(request, alert_id):
    alert = get_object_or_404(Alert, id=alert_id)
    if unmerge_alert(alert, request.user, request):
        messages.success(request, 'Alert unmerged and returned to the queue.')
    else:
        messages.info(request, 'This alert is not merged.')
    return redirect('alerts:detail', alert_id=alert.id)


@login_required
@permission_required('can_change_verdict')
@require_POST
def alert_report_fp(request, alert_id):
    """Phase 9: record a false-positive report and mark the alert verdict."""
    alert = get_object_or_404(Alert, id=alert_id)
    reason = (request.POST.get('reason') or '').strip()
    FalsePositiveReport.objects.create(
        alert=alert,
        rule_id=alert.rule_id or '',
        reason=reason,
        reported_by=request.user,
    )
    alert.verdict = 'False Positive'
    alert.save(update_fields=['verdict'], recalc_sla=False)
    create_audit_log(
        alert, request.user, 'FP Reported',
        f'False positive reported: {reason}' if reason else 'False positive reported',
        request,
    )
    messages.success(request, 'Reported as false positive. This feeds the rule-tuning dashboard.')
    return redirect('alerts:detail', alert_id=alert.id)

