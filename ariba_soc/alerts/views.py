import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib.auth.models import User
from accounts.models import SocTeam
from settings_manager.models import SeveritySettings, StatusSettings, VerdictSettings
from accounts.decorators import role_required, permission_required, TIER_ORDER
from .models import (
    Alert, AlertComment, AlertAuditLog, Notification,
    AlertEscalation, AlertTransition,
)
from .forms import AlertEditForm, AlertCommentForm
from .services import update_alert, assign_alert, create_audit_log, _notify_escalation
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
def alert_table(request):
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

    allowed_sorts = ['alert_time', '-alert_time', 'severity', '-severity', 'status', '-status', 'verdict', '-verdict', 'alert_name', '-alert_name', 'wazuh_alert_id', '-wazuh_alert_id']
    if sort in allowed_sorts:
        alerts = alerts.order_by(sort)
    else:
        alerts = alerts.order_by('-alert_time')

    paginator = Paginator(alerts, 25)
    page = request.GET.get('page', 1)
    alerts_page = paginator.get_page(page)

    assignees = Alert.objects.exclude(assignee__isnull=True).values_list('assignee_id', 'assignee__username').distinct()
    soc_teams = SocTeam.objects.filter(is_active=True).order_by('tier', 'name')

    context = {
        'alerts': alerts_page,
        'assignees': assignees,
        'users': User.objects.filter(is_active=True),
        'soc_teams': soc_teams,
        'user_soc_team': user_soc_team,
        'severities': SeveritySettings.objects.filter(is_active=True).order_by('sort_order'),
        'statuses': StatusSettings.objects.filter(is_active=True).order_by('sort_order'),
        'verdicts': VerdictSettings.objects.filter(is_active=True).order_by('name'),
        'current_filters': {
            'search': search, 'severity': severity, 'status': status,
            'verdict': verdict, 'assignee': assignee, 'team': team,
            'date_from': date_from, 'date_to': date_to, 'sort': sort,
        },
        'is_paginated': alerts_page.has_other_pages(),
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
    return render(request, 'ariba_soc/alert_detail.html', {
        'alert': alert, 'comments': comments, 'audit_logs': audit_logs,
        'transitions': transitions, 'escalation_records': escalation_records,
        'form': form, 'users': User.objects.filter(is_active=True),
        'soc_teams': soc_teams,
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
    data = json.loads(request.body)
    new_status = data.get('status')
    allowed_statuses = list(StatusSettings.objects.filter(is_active=True).values_list('name', flat=True))
    if new_status and new_status in allowed_statuses:
        old = alert.status
        alert.status = new_status
        if new_status == 'In Progress':
            alert.acknowledged_at = alert.acknowledged_at or timezone.now()
        alert.save()
        create_audit_log(alert, request.user, 'Status Changed', old, new_status, request)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)


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

