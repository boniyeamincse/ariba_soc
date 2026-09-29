from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.db.models import Q, Sum, Count
from accounts.models import AnalystProfile, RolePermission, ROLE_CHOICES, SETTINGS_ALLOWED_ROLES as _FALLBACK_SETTINGS_ROLES
from .models import (
    AlertSourceSettings, SeveritySettings, StatusSettings, VerdictSettings,
    SLASettings, EscalationRule, NotificationSetting, ReportSetting,
    DashboardSetting, AuditLogSetting, AlarmSetting, AlarmSystemSetting, SystemSetting, SettingAuditLog,
    IOCEnrichmentSetting, AlertAggregationSetting, AlertSuppressionRule
)
from .forms import (
    UserManagementForm, UserEditForm, AnalystProfileForm,
    AlertSourceSettingsForm, SeveritySettingsForm, StatusSettingsForm,
    VerdictSettingsForm, SLASettingsForm, EscalationRuleForm,
    NotificationSettingForm, ReportSettingForm, DashboardSettingForm,
    AuditLogSettingForm, AlarmSettingForm, AlarmSystemSettingForm, SystemSettingForm, ResetPasswordForm,
    IOCEnrichmentSettingForm, AlertAggregationSettingForm, AlertSuppressionRuleForm
)

def _get_allowed_roles():
    stored = SystemSetting.get_setting('settings_allowed_roles', '')
    if stored:
        return [r.strip() for r in stored.split(',')]
    return _FALLBACK_SETTINGS_ROLES


def _check_settings_access(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = getattr(user, 'analyst_profile', None)
    role = profile.role if profile else ''
    return role in _get_allowed_roles()

def _log_setting_change(user, action, model_name, obj_id, old_val, new_val, request):
    ip = request.META.get('REMOTE_ADDR', '') if request else ''
    SettingAuditLog.objects.create(
        user=user, action=action, model_name=model_name,
        object_id=obj_id, old_value=str(old_val), new_value=str(new_val), ip_address=ip
    )

def settings_dashboard(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    ctx = {
        'section': 'dashboard',
        'user_count': User.objects.filter(is_active=True).count(),
        'source_count': AlertSourceSettings.objects.count(),
        'severity_count': SeveritySettings.objects.count(),
        'status_count': StatusSettings.objects.count(),
        'verdict_count': VerdictSettings.objects.count(),
        'sla_count': SLASettings.objects.count(),
        'escalation_count': EscalationRule.objects.filter(is_active=True).count(),
        'alarm_count': AlarmSetting.objects.count(),
        'alarm_enabled_count': AlarmSetting.objects.filter(is_enabled=True).count(),
        'agg_setting': AlertAggregationSetting.load(),
        'suppression_count': AlertSuppressionRule.objects.filter(is_active=True).count(),
        'recent_logs': SettingAuditLog.objects.select_related('user').all()[:10],
    }
    return render(request, 'settings_manager/settings_dashboard.html', ctx)

def user_management(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')

    search = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    team_filter = request.GET.get('team', '')
    status_filter = request.GET.get('status', '')

    users = User.objects.select_related('analyst_profile').all().order_by('username')

    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
    if role_filter:
        users = users.filter(analyst_profile__role=role_filter)
    if team_filter:
        users = users.filter(analyst_profile__team=team_filter)
    if status_filter == 'active':
        users = users.filter(analyst_profile__is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(analyst_profile__is_active=False)

    if request.method == 'POST' and 'create' in request.POST:
        form = UserManagementForm(request.POST)
        if form.is_valid():
            user = form.save()
            _log_setting_change(request.user, f'Created user {user.username}', 'User', user.id, '', 'Created', request)
            messages.success(request, f'User {user.username} created.')
            return redirect('settings:user_management')
    else:
        form = UserManagementForm()

    from accounts.models import TEAM_CHOICES
    total_users = User.objects.count()
    active_users = User.objects.filter(analyst_profile__is_active=True).count()
    inactive_users = total_users - active_users
    role_counts = {r[0]: {'label': r[1], 'count': User.objects.filter(analyst_profile__role=r[0]).count()} for r in ROLE_CHOICES}

    ctx = {
        'section': 'users',
        'users': users,
        'form': form,
        'search': search,
        'role_filter': role_filter,
        'team_filter': team_filter,
        'status_filter': status_filter,
        'role_choices': ROLE_CHOICES,
        'team_choices': TEAM_CHOICES,
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'role_counts': role_counts,
    }
    return render(request, 'settings_manager/user_management.html', ctx)


@require_POST
def user_delete(request, user_id):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    user = get_object_or_404(User, id=user_id)
    if user == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('settings:user_management')
    if user.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
        messages.error(request, 'Cannot delete the only admin account.')
        return redirect('settings:user_management')
    username = user.username
    _log_setting_change(request.user, f'Deleted user {username}', 'User', user.id, username, 'Deleted', request)
    user.delete()
    messages.success(request, f'User "{username}" permanently deleted.')
    return redirect('settings:user_management')


@require_POST
def user_bulk_action(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    action = request.POST.get('action', '')
    user_ids = request.POST.getlist('user_ids')
    if not user_ids:
        messages.warning(request, 'No users selected.')
        return redirect('settings:user_management')

    users_qs = User.objects.filter(id__in=user_ids).exclude(id=request.user.id).select_related('analyst_profile')
    count = 0

    if action == 'activate':
        for u in users_qs:
            profile = getattr(u, 'analyst_profile', None)
            if profile and not profile.is_active:
                profile.is_active = True
                profile.save()
                u.is_active = True
                u.save()
                count += 1
        messages.success(request, f'Activated {count} user(s).')
    elif action == 'deactivate':
        for u in users_qs:
            if u.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
                continue
            profile = getattr(u, 'analyst_profile', None)
            if profile and profile.is_active:
                profile.is_active = False
                profile.save()
                u.is_active = False
                u.save()
                count += 1
        messages.success(request, f'Deactivated {count} user(s).')
    elif action == 'delete':
        for u in users_qs:
            if u.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
                continue
            _log_setting_change(request.user, f'Bulk deleted user {u.username}', 'User', u.id, u.username, 'Deleted', request)
            u.delete()
            count += 1
        messages.success(request, f'Deleted {count} user(s).')
    elif action.startswith('role:'):
        new_role = action.split(':', 1)[1]
        valid_roles = [r[0] for r in ROLE_CHOICES]
        if new_role in valid_roles:
            for u in users_qs:
                profile = getattr(u, 'analyst_profile', None)
                if profile:
                    old_role = profile.role
                    profile.role = new_role
                    profile.save()
                    _log_setting_change(request.user, f'Bulk role change {u.username}: {old_role} -> {new_role}', 'User', u.id, old_role, new_role, request)
                    count += 1
            messages.success(request, f'Updated role to {new_role} for {count} user(s).')
        else:
            messages.error(request, 'Invalid role specified.')
    else:
        messages.error(request, 'Unknown bulk action.')

    return redirect('settings:user_management')


def user_export_csv(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    import csv
    from django.http import HttpResponse
    from django.utils.timezone import localtime
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="soc_users_export.csv"'
    writer = csv.writer(response)
    writer.writerow(['Username', 'First Name', 'Last Name', 'Email', 'Role', 'Team', 'Phone', 'Designation', 'Active', 'Superuser', 'Last Login', 'Date Joined'])
    for u in User.objects.select_related('analyst_profile').all().order_by('username'):
        p = getattr(u, 'analyst_profile', None)
        writer.writerow([
            u.username, u.first_name, u.last_name, u.email,
            getattr(p, 'role', ''), getattr(p, 'team', ''),
            getattr(p, 'phone', ''), getattr(p, 'designation', ''),
            'Yes' if getattr(p, 'is_active', True) else 'No',
            'Yes' if u.is_superuser else 'No',
            localtime(u.last_login).strftime('%Y-%m-%d %H:%M') if u.last_login else '',
            localtime(u.date_joined).strftime('%Y-%m-%d %H:%M') if u.date_joined else '',
        ])
    _log_setting_change(request.user, 'Exported user list as CSV', 'User', 0, '', 'CSV Export', request)
    return response


def user_edit(request, user_id):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    user = get_object_or_404(User.objects.select_related('analyst_profile'), id=user_id)
    if request.method == 'POST':
        form = UserEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save(files=request.FILES)
            _log_setting_change(request.user, f'Edited user {user.username}', 'User', user.id, '', 'Updated', request)
            messages.success(request, 'User updated.')
            return redirect('settings:user_management')
    else:
        form = UserEditForm(instance=user)
    ctx = {'section': 'users', 'form': form, 'edit_user': user}
    return render(request, 'settings_manager/user_edit.html', ctx)


@require_POST
def user_toggle_active(request, user_id):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    user = get_object_or_404(User, id=user_id)
    if user.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
        messages.error(request, 'Cannot disable the only admin.')
        return redirect('settings:user_management')
    profile = getattr(user, 'analyst_profile', None)
    if profile:
        profile.is_active = not profile.is_active
        profile.save()
    user.is_active = profile.is_active
    user.save()
    _log_setting_change(request.user, f'{"Activated" if user.is_active else "Deactivated"} user {user.username}', 'User', user.id, '', f'Active={user.is_active}', request)
    messages.success(request, f'User {"activated" if user.is_active else "deactivated"}.')
    return redirect('settings:user_management')

def user_reset_password(request, user_id):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['new_password'])
            user.save()
            _log_setting_change(request.user, f'Reset password for {user.username}', 'User', user.id, '', 'Password Reset', request)
            messages.success(request, 'Password reset.')
            return redirect('settings:user_management')
    else:
        form = ResetPasswordForm()
    ctx = {'section': 'users', 'form': form, 'edit_user': user}
    return render(request, 'settings_manager/user_reset_password.html', ctx)

def role_permission(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')

    # All permissions shown in the matrix, grouped by category
    PERMISSION_GROUPS = [
        ('Alert Triage', [
            ('View Alerts', 'can_view_alerts'),
            ('Assign to Self', 'can_assign_self'),
            ('Assign to Others', 'can_assign_others'),
            ('Reassign', 'can_reassign'),
            ('Change Status', 'can_change_status'),
            ('Change Severity', 'can_change_severity'),
            ('Change Verdict', 'can_change_verdict'),
            ('Close Alert', 'can_close_alert'),
            ('Escalate Alert', 'can_escalate_alert'),
            ('Archive', 'can_archive'),
        ]),
        ('Incidents', [
            ('View Incidents', 'can_view_incidents'),
            ('Create Incident', 'can_create_incident'),
            ('Mark Alert as Incident', 'can_mark_incident'),
            ('Assign Incident', 'can_assign_incident'),
            ('Manage Incident', 'can_manage_incident'),
            ('Close Incident', 'can_close_incident'),
            ('Reopen Incident', 'can_reopen_incident'),
            ('Link Alerts to Incident', 'can_link_incident_alerts'),
        ]),
        ('Remediation', [
            ('Add Remediation', 'can_add_remediation'),
        ]),
        ('Threat Hunting', [
            ('Basic Hunting', 'can_use_basic_hunting'),
            ('Advanced Hunting', 'can_use_advanced_hunting'),
        ]),
        ('Reports', [
            ('View Reports', 'can_view_reports'),
            ('Export Reports', 'can_export_reports'),
        ]),
        ('Administration', [
            ('Manage Users', 'can_manage_users'),
            ('Manage Wazuh', 'can_manage_wazuh'),
            ('View Audit Logs', 'can_view_audit_logs'),
        ]),
    ]

    # Flat list of all permission field names shown in the UI
    ALL_UI_FIELDS = [pf for _, perms in PERMISSION_GROUPS for _, pf in perms]

    roles = RolePermission.objects.all()
    role_map = {rp.role: rp for rp in roles}

    if request.method == 'POST':
        for role_choice, _ in ROLE_CHOICES:
            rc = role_choice if not isinstance(role_choice, tuple) else role_choice[0]
            rp, _ = RolePermission.objects.get_or_create(role=rc)
            # Only update the fields that are rendered in the UI — never touch hidden fields
            for field in ALL_UI_FIELDS:
                val = request.POST.get(f'{rp.role}_{field}') == 'on'
                setattr(rp, field, val)
            rp.save()
        _log_setting_change(request.user, 'Updated role permissions', 'RolePermission', 0, '', 'Updated', request)
        messages.success(request, 'Permissions saved.')
        return redirect('settings:role_permission')

    # Count users per role for column header
    role_user_counts = {}
    for rc, label in ROLE_CHOICES:
        role_user_counts[rc] = User.objects.filter(analyst_profile__role=rc).count()

    ctx = {
        'section': 'roles',
        'roles': roles,
        'role_map': role_map,
        'role_choices': ROLE_CHOICES,
        'permission_groups': PERMISSION_GROUPS,
        'all_ui_fields': ALL_UI_FIELDS,
        'role_user_counts': role_user_counts,
    }
    return render(request, 'settings_manager/role_permission.html', ctx)

def analyst_profile_list(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    search = request.GET.get('search', '')
    profiles = AnalystProfile.objects.select_related('user').all()
    if search:
        profiles = profiles.filter(Q(user__username__icontains=search) | Q(user__first_name__icontains=search) | Q(designation__icontains=search))
    if request.method == 'POST' and 'update' in request.POST:
        pid = request.POST.get('profile_id')
        profile = get_object_or_404(AnalystProfile, id=pid)
        form = AnalystProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, f'Updated profile {profile.user.username}', 'AnalystProfile', profile.id, '', 'Updated', request)
            messages.success(request, 'Profile updated.')
            return redirect('settings:analyst_profile')
    else:
        form = AnalystProfileForm()
    ctx = {'section': 'analysts', 'profiles': profiles, 'form': form, 'search': search}
    return render(request, 'settings_manager/analyst_profile.html', ctx)

def wazuh_api_settings(request):
    return redirect('wazuh_integration:status')

def alert_source_settings(request):
    return redirect('wazuh_integration:status')

def alert_source_edit(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(AlertSourceSettings, id=pk)
    if request.method == 'POST':
        form = AlertSourceSettingsForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, f'Edited alert source {obj.name}', 'AlertSourceSettings', obj.id, '', 'Updated', request)
            messages.success(request, 'Source updated.')
            return redirect('settings:alert_sources')
    else:
        form = AlertSourceSettingsForm(instance=obj)
    ctx = {'section': 'sources', 'form': form, 'object': obj}
    return render(request, 'settings_manager/alert_source_edit.html', ctx)

@require_POST
def alert_source_toggle(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(AlertSourceSettings, id=pk)
    obj.is_active = not obj.is_active
    obj.save()
    _log_setting_change(request.user, f'{"Activated" if obj.is_active else "Deactivated"} source {obj.name}', 'AlertSourceSettings', obj.id, '', f'Active={obj.is_active}', request)
    messages.success(request, f'Source {"activated" if obj.is_active else "deactivated"}.')
    return redirect('settings:alert_sources')

@require_POST
def alert_source_delete(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(AlertSourceSettings, id=pk)
    name = obj.name
    _log_setting_change(request.user, f'Deleted alert source {name}', 'AlertSourceSettings', obj.id, name, 'Deleted', request)
    obj.delete()
    messages.success(request, f'Alert Source "{name}" permanently deleted.')
    return redirect('settings:alert_sources')

def severity_settings(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    severities = SeveritySettings.objects.all()
    if request.method == 'POST':
        form = SeveritySettingsForm(request.POST)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, 'Created severity', 'SeveritySettings', 0, '', form.cleaned_data['name'], request)
            messages.success(request, 'Severity created.')
            return redirect('settings:severities')
    else:
        form = SeveritySettingsForm()
    ctx = {'section': 'severities', 'severities': severities, 'form': form}
    return render(request, 'settings_manager/severity_settings.html', ctx)

def severity_edit(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(SeveritySettings, id=pk)
    if request.method == 'POST':
        form = SeveritySettingsForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, f'Edited severity {obj.name}', 'SeveritySettings', obj.id, '', 'Updated', request)
            messages.success(request, 'Severity updated.')
            return redirect('settings:severities')
    else:
        form = SeveritySettingsForm(instance=obj)
    ctx = {'section': 'severities', 'form': form, 'object': obj}
    return render(request, 'settings_manager/severity_edit.html', ctx)

@require_POST
def severity_toggle(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(SeveritySettings, id=pk)
    obj.is_active = not obj.is_active
    obj.save()
    messages.success(request, f'Severity {"activated" if obj.is_active else "deactivated"}.')
    return redirect('settings:severities')

@require_POST
def severity_delete(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(SeveritySettings, id=pk)
    name = obj.name
    _log_setting_change(request.user, f'Deleted severity {name}', 'SeveritySettings', obj.id, name, 'Deleted', request)
    obj.delete()
    messages.success(request, f'Severity "{name}" permanently deleted.')
    return redirect('settings:severities')

def status_settings(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    statuses = StatusSettings.objects.all()
    if request.method == 'POST':
        form = StatusSettingsForm(request.POST)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, 'Created status', 'StatusSettings', 0, '', form.cleaned_data['name'], request)
            messages.success(request, 'Status created.')
            return redirect('settings:statuses')
    else:
        form = StatusSettingsForm()
    ctx = {'section': 'statuses', 'statuses': statuses, 'form': form}
    return render(request, 'settings_manager/status_settings.html', ctx)

def status_edit(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(StatusSettings, id=pk)
    if request.method == 'POST':
        form = StatusSettingsForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, f'Edited status {obj.name}', 'StatusSettings', obj.id, '', 'Updated', request)
            messages.success(request, 'Status updated.')
            return redirect('settings:statuses')
    else:
        form = StatusSettingsForm(instance=obj)
    ctx = {'section': 'statuses', 'form': form, 'object': obj}
    return render(request, 'settings_manager/status_edit.html', ctx)

@require_POST
def status_toggle(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(StatusSettings, id=pk)
    obj.is_active = not obj.is_active
    obj.save()
    messages.success(request, f'Status {"activated" if obj.is_active else "deactivated"}.')
    return redirect('settings:statuses')

@require_POST
def status_delete(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(StatusSettings, id=pk)
    name = obj.name
    _log_setting_change(request.user, f'Deleted status {name}', 'StatusSettings', obj.id, name, 'Deleted', request)
    obj.delete()
    messages.success(request, f'Status "{name}" permanently deleted.')
    return redirect('settings:statuses')

def verdict_settings(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    verdicts = VerdictSettings.objects.all()
    if request.method == 'POST':
        form = VerdictSettingsForm(request.POST)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, 'Created verdict', 'VerdictSettings', 0, '', form.cleaned_data['name'], request)
            messages.success(request, 'Verdict created.')
            return redirect('settings:verdicts')
    else:
        form = VerdictSettingsForm()
    ctx = {'section': 'verdicts', 'verdicts': verdicts, 'form': form}
    return render(request, 'settings_manager/verdict_settings.html', ctx)

def verdict_edit(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(VerdictSettings, id=pk)
    if request.method == 'POST':
        form = VerdictSettingsForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, f'Edited verdict {obj.name}', 'VerdictSettings', obj.id, '', 'Updated', request)
            messages.success(request, 'Verdict updated.')
            return redirect('settings:verdicts')
    else:
        form = VerdictSettingsForm(instance=obj)
    ctx = {'section': 'verdicts', 'form': form, 'object': obj}
    return render(request, 'settings_manager/verdict_edit.html', ctx)

@require_POST
def verdict_toggle(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(VerdictSettings, id=pk)
    obj.is_active = not obj.is_active
    obj.save()
    messages.success(request, f'Verdict {"activated" if obj.is_active else "deactivated"}.')
    return redirect('settings:verdicts')

@require_POST
def verdict_delete(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(VerdictSettings, id=pk)
    name = obj.name
    _log_setting_change(request.user, f'Deleted verdict {name}', 'VerdictSettings', obj.id, name, 'Deleted', request)
    obj.delete()
    messages.success(request, f'Verdict "{name}" permanently deleted.')
    return redirect('settings:verdicts')

def sla_settings(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    slas = SLASettings.objects.all()
    if request.method == 'POST':
        form = SLASettingsForm(request.POST)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, 'Created SLA', 'SLASettings', 0, '', form.cleaned_data['severity'], request)
            messages.success(request, 'SLA created.')
            return redirect('settings:sla')
    else:
        form = SLASettingsForm()
    ctx = {'section': 'sla', 'slas': slas, 'form': form}
    return render(request, 'settings_manager/sla_settings.html', ctx)

def sla_edit(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(SLASettings, id=pk)
    if request.method == 'POST':
        form = SLASettingsForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, f'Edited SLA for {obj.severity}', 'SLASettings', obj.id, '', 'Updated', request)
            messages.success(request, 'SLA updated.')
            return redirect('settings:sla')
    else:
        form = SLASettingsForm(instance=obj)
    ctx = {'section': 'sla', 'form': form, 'object': obj}
    return render(request, 'settings_manager/sla_edit.html', ctx)

@require_POST
def sla_toggle(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(SLASettings, id=pk)
    obj.is_active = not obj.is_active
    obj.save()
    messages.success(request, f'SLA {"activated" if obj.is_active else "deactivated"}.')
    return redirect('settings:sla')

@require_POST
def sla_delete(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(SLASettings, id=pk)
    name = str(obj.severity)
    _log_setting_change(request.user, f'Deleted SLA for severity {name}', 'SLASettings', obj.id, name, 'Deleted', request)
    obj.delete()
    messages.success(request, f'SLA for "{name}" permanently deleted.')
    return redirect('settings:sla')

def escalation_settings(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    rules = EscalationRule.objects.all()
    if request.method == 'POST':
        form = EscalationRuleForm(request.POST)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, 'Created escalation rule', 'EscalationRule', 0, '', form.cleaned_data['rule_name'], request)
            messages.success(request, 'Rule created.')
            return redirect('settings:escalation')
    else:
        form = EscalationRuleForm()
    ctx = {'section': 'escalation', 'rules': rules, 'form': form}
    return render(request, 'settings_manager/escalation_settings.html', ctx)

def escalation_edit(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(EscalationRule, id=pk)
    if request.method == 'POST':
        form = EscalationRuleForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, f'Edited escalation rule {obj.rule_name}', 'EscalationRule', obj.id, '', 'Updated', request)
            messages.success(request, 'Rule updated.')
            return redirect('settings:escalation')
    else:
        form = EscalationRuleForm(instance=obj)
    ctx = {'section': 'escalation', 'form': form, 'object': obj}
    return render(request, 'settings_manager/escalation_edit.html', ctx)

@require_POST
def escalation_toggle(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(EscalationRule, id=pk)
    obj.is_active = not obj.is_active
    obj.save()
    messages.success(request, f'Rule {"activated" if obj.is_active else "deactivated"}.')
    return redirect('settings:escalation')

@require_POST
def escalation_delete(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(EscalationRule, id=pk)
    name = obj.rule_name
    _log_setting_change(request.user, f'Deleted escalation rule {name}', 'EscalationRule', obj.id, name, 'Deleted', request)
    obj.delete()
    messages.success(request, f'Escalation Rule "{name}" permanently deleted.')
    return redirect('settings:escalation')

def notification_settings(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    notifs = NotificationSetting.objects.all()
    if request.method == 'POST':
        form = NotificationSettingForm(request.POST)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, 'Created notification setting', 'NotificationSetting', 0, '', form.cleaned_data['name'], request)
            messages.success(request, 'Notification created.')
            return redirect('settings:notifications')
    else:
        form = NotificationSettingForm()
    ctx = {'section': 'notifications', 'notifications': notifs, 'form': form}
    return render(request, 'settings_manager/notification_settings.html', ctx)

def notification_edit(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(NotificationSetting, id=pk)
    if request.method == 'POST':
        form = NotificationSettingForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, f'Edited notification {obj.name}', 'NotificationSetting', obj.id, '', 'Updated', request)
            messages.success(request, 'Notification updated.')
            return redirect('settings:notifications')
    else:
        form = NotificationSettingForm(instance=obj)
    ctx = {'section': 'notifications', 'form': form, 'object': obj}
    return render(request, 'settings_manager/notification_edit.html', ctx)

@require_POST
def notification_toggle(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(NotificationSetting, id=pk)
    obj.is_active = not obj.is_active
    obj.save()
    messages.success(request, f'Notification {"activated" if obj.is_active else "deactivated"}.')
    return redirect('settings:notifications')

def report_settings(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    reports = ReportSetting.objects.all()
    if request.method == 'POST':
        form = ReportSettingForm(request.POST)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, 'Created report setting', 'ReportSetting', 0, '', form.cleaned_data['name'], request)
            messages.success(request, 'Report setting created.')
            return redirect('settings:reports')
    else:
        form = ReportSettingForm()
    ctx = {'section': 'reports', 'reports': reports, 'form': form}
    return render(request, 'settings_manager/report_settings.html', ctx)

def report_edit(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(ReportSetting, id=pk)
    if request.method == 'POST':
        form = ReportSettingForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, f'Edited report setting {obj.name}', 'ReportSetting', obj.id, '', 'Updated', request)
            messages.success(request, 'Report setting updated.')
            return redirect('settings:reports')
    else:
        form = ReportSettingForm(instance=obj)
    ctx = {'section': 'reports', 'form': form, 'object': obj}
    return render(request, 'settings_manager/report_edit.html', ctx)

@require_POST
def report_toggle(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(ReportSetting, id=pk)
    obj.is_active = not obj.is_active
    obj.save()
    messages.success(request, f'Report setting {"activated" if obj.is_active else "deactivated"}.')
    return redirect('settings:reports')

def dashboard_settings(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    dashboards = DashboardSetting.objects.all()
    if request.method == 'POST':
        form = DashboardSettingForm(request.POST)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, 'Created dashboard setting', 'DashboardSetting', 0, '', form.cleaned_data['role'], request)
            messages.success(request, 'Dashboard setting created.')
            return redirect('settings:dashboard')
    else:
        form = DashboardSettingForm()
    ctx = {'section': 'dashboard', 'dashboards': dashboards, 'form': form}
    return render(request, 'settings_manager/dashboard_settings.html', ctx)

def dashboard_edit(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(DashboardSetting, id=pk)
    if request.method == 'POST':
        form = DashboardSettingForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, f'Edited dashboard setting for {obj.get_role_display()}', 'DashboardSetting', obj.id, '', 'Updated', request)
            messages.success(request, 'Dashboard setting updated.')
            return redirect('settings:dashboard')
    else:
        form = DashboardSettingForm(instance=obj)
    ctx = {'section': 'dashboard', 'form': form, 'object': obj}
    return render(request, 'settings_manager/dashboard_edit.html', ctx)

def audit_log_settings(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    logs = AuditLogSetting.objects.all()
    if request.method == 'POST':
        form = AuditLogSettingForm(request.POST)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, 'Created audit log setting', 'AuditLogSetting', 0, '', form.cleaned_data['action_type'], request)
            messages.success(request, 'Audit log setting created.')
            return redirect('settings:audit_log')
    else:
        form = AuditLogSettingForm()
    ctx = {'section': 'audit_log', 'logs': logs, 'form': form}
    return render(request, 'settings_manager/audit_log_settings.html', ctx)

def audit_log_edit(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(AuditLogSetting, id=pk)
    if request.method == 'POST':
        form = AuditLogSettingForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, f'Edited audit log setting {obj.action_type}', 'AuditLogSetting', obj.id, '', 'Updated', request)
            messages.success(request, 'Audit log setting updated.')
            return redirect('settings:audit_log')
    else:
        form = AuditLogSettingForm(instance=obj)
    ctx = {'section': 'audit_log', 'form': form, 'object': obj}
    return render(request, 'settings_manager/audit_log_edit.html', ctx)

@require_POST
def audit_log_toggle(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(AuditLogSetting, id=pk)
    obj.log_enabled = not obj.log_enabled
    obj.save()
    messages.success(request, f'Audit logging {"enabled" if obj.log_enabled else "disabled"} for {obj.action_type}.')
    return redirect('settings:audit_log')

def system_settings(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    settings_list = SystemSetting.objects.all()
    if request.method == 'POST':
        form = SystemSettingForm(request.POST)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, 'Created system setting', 'SystemSetting', 0, '', form.cleaned_data['key'], request)
            messages.success(request, 'Setting saved.')
            return redirect('settings:system')
    else:
        form = SystemSettingForm()
    ctx = {'section': 'system', 'settings_list': settings_list, 'form': form}
    return render(request, 'settings_manager/system_settings.html', ctx)

def system_edit(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    obj = get_object_or_404(SystemSetting, id=pk)
    if request.method == 'POST':
        form = SystemSettingForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, f'Edited system setting {obj.key}', 'SystemSetting', obj.id, '', 'Updated', request)
            messages.success(request, 'Setting updated.')
            return redirect('settings:system')
    else:
        form = SystemSettingForm(instance=obj)
    ctx = {'section': 'system', 'form': form, 'object': obj}
    return render(request, 'settings_manager/system_edit.html', ctx)

def alarm_settings(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    alarms = AlarmSetting.objects.all()
    alarm_system = AlarmSystemSetting.load()
    if request.method == 'POST':
        form = AlarmSystemSettingForm(request.POST, request.FILES, instance=alarm_system)
        if form.is_valid():
            form.save()
            _log_setting_change(
                request.user,
                'Updated alarm system configuration',
                'AlarmSystemSetting',
                alarm_system.id if alarm_system.id else 1,
                '',
                'Updated',
                request,
            )
            messages.success(request, 'Alarm system configuration saved.')
            return redirect('settings:alarms')
    else:
        form = AlarmSystemSettingForm(instance=alarm_system)
    ctx = {
        'section': 'alarms',
        'alarms': alarms,
        'alarm_master_enabled': AlarmSetting.system_enabled(),
        'alarm_system_form': form,
        'alarm_system': alarm_system,
    }
    return render(request, 'settings_manager/alarm_settings.html', ctx)

@require_POST
def alarm_master_toggle(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    alarm_system = AlarmSystemSetting.load()
    alarm_system.is_enabled = not alarm_system.is_enabled
    alarm_system.save(update_fields=['is_enabled', 'updated_at'])
    _log_setting_change(
        request.user,
        f'{"Enabled" if alarm_system.is_enabled else "Disabled"} alarm system',
        'AlarmSystemSetting',
        alarm_system.id,
        '',
        f'Enabled={alarm_system.is_enabled}',
        request,
    )
    messages.success(request, f'Alarm system {"enabled" if alarm_system.is_enabled else "disabled"}.')
    return redirect('settings:alarms')

@require_POST
def alarm_toggle(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    alarm = get_object_or_404(AlarmSetting, id=pk)
    alarm.is_enabled = not alarm.is_enabled
    alarm.save()
    _log_setting_change(
        request.user,
        f'{"Enabled" if alarm.is_enabled else "Disabled"} alarm severity {alarm.severity}',
        'AlarmSetting',
        alarm.id,
        '',
        f'Enabled={alarm.is_enabled}',
        request,
    )
    messages.success(request, f'{alarm.severity} alarm {"enabled" if alarm.is_enabled else "disabled"}.')
    return redirect('settings:alarms')

@login_required
@require_POST
def alarm_stop(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'auth_required'}, status=403)
    alarm_system = AlarmSystemSetting.stop_alarm()
    return JsonResponse({
        'success': True,
        'active': alarm_system.is_active,
        'enabled': alarm_system.is_enabled,
    })

@login_required
def alarm_state(request):
    alarm_system = AlarmSystemSetting.load()
    data = {
        'success': True,
        'enabled': alarm_system.is_enabled,
        'active': alarm_system.is_active and alarm_system.is_enabled,
        'active_alert_id': alarm_system.active_alert_id,
        'active_alert_name': alarm_system.active_alert_name,
        'active_severity': alarm_system.active_severity,
        'active_message': alarm_system.active_message,
        'sound_url': alarm_system.sound_file.url if alarm_system.sound_file else '',
        'triggered_at': alarm_system.triggered_at.isoformat() if alarm_system.triggered_at else '',
        'acknowledged_at': alarm_system.acknowledged_at.isoformat() if alarm_system.acknowledged_at else '',
    }
    return JsonResponse(data)

@login_required
def ioc_enrichment_list(request):
    profile = getattr(request.user, 'analyst_profile', None)
    if not profile or profile.role not in ['ADMIN', 'SOC_MGR']:
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
        
    settings_list = IOCEnrichmentSetting.objects.all()
    if request.method == 'POST':
        form = IOCEnrichmentSettingForm(request.POST)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, f"Created IOC Enrichment Setting: {form.cleaned_data['provider_name']}", 'IOCEnrichmentSetting', 0, '', 'Created', request)
            messages.success(request, 'IOC Enrichment setting added successfully.')
            return redirect('settings:ioc_enrichment')
    else:
        form = IOCEnrichmentSettingForm()
    
    ctx = {'section': 'ioc_enrichment', 'settings_list': settings_list, 'form': form, 'title': 'IOC Enrichment Settings'}
    return render(request, 'settings_manager/ioc_enrichment.html', ctx)

@login_required
def ioc_enrichment_update(request, pk):
    profile = getattr(request.user, 'analyst_profile', None)
    if not profile or profile.role not in ['ADMIN', 'SOC_MGR']:
        messages.error(request, 'Access denied.')
        return redirect('dashboard:home')
        
    setting = get_object_or_404(IOCEnrichmentSetting, pk=pk)
    if request.method == 'POST':
        if 'delete' in request.POST:
            name = setting.provider_name
            setting.delete()
            _log_setting_change(request.user, f"Deleted IOC Enrichment Setting: {name}", 'IOCEnrichmentSetting', pk, '', 'Deleted', request)
            messages.success(request, 'Setting deleted successfully.')
            return redirect('settings:ioc_enrichment')
            
        form = IOCEnrichmentSettingForm(request.POST, instance=setting)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, f"Updated IOC Enrichment Setting: {setting.provider_name}", 'IOCEnrichmentSetting', pk, '', 'Updated', request)
            messages.success(request, 'Setting updated successfully.')
            return redirect('settings:ioc_enrichment')
    else:
        form = IOCEnrichmentSettingForm(instance=setting)
        
    ctx = {'section': 'ioc_enrichment', 'form': form, 'edit_mode': True, 'edit_obj': setting, 'title': 'Edit IOC Enrichment Setting'}
    return render(request, 'settings_manager/ioc_enrichment.html', ctx)


def aggregation_settings(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    agg_setting = AlertAggregationSetting.load()
    if request.method == 'POST':
        form = AlertAggregationSettingForm(request.POST, instance=agg_setting)
        if form.is_valid():
            form.save()
            _log_setting_change(
                request.user,
                'Updated alert aggregation configuration',
                'AlertAggregationSetting',
                agg_setting.id if agg_setting.id else 1,
                '',
                'Updated',
                request,
            )
            messages.success(request, 'Alert aggregation configuration saved successfully.')
            return redirect('settings:aggregation')
    else:
        form = AlertAggregationSettingForm(instance=agg_setting)

    from alerts.models import Alert
    total_alerts = Alert.objects.count()
    aggregated_alerts = Alert.objects.filter(event_count__gt=1).count()
    total_events_saved = (
        Alert.objects.filter(event_count__gt=1).aggregate(
            saved=Sum('event_count') - Count('id')
        )['saved'] or 0
    ) if aggregated_alerts > 0 else 0

    ctx = {
        'section': 'aggregation',
        'form': form,
        'agg_setting': agg_setting,
        'total_alerts': total_alerts,
        'aggregated_alerts': aggregated_alerts,
        'total_events_saved': total_events_saved,
    }
    return render(request, 'settings_manager/aggregation_settings.html', ctx)


@require_POST
def aggregation_toggle(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    agg_setting = AlertAggregationSetting.load()
    agg_setting.is_enabled = not agg_setting.is_enabled
    agg_setting.save(update_fields=['is_enabled', 'updated_at'])
    _log_setting_change(
        request.user,
        f'{"Enabled" if agg_setting.is_enabled else "Disabled"} alert aggregation',
        'AlertAggregationSetting',
        agg_setting.id,
        '',
        f'Enabled={agg_setting.is_enabled}',
        request,
    )
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok', 'is_enabled': agg_setting.is_enabled})
    messages.success(request, f'Alert aggregation {"enabled" if agg_setting.is_enabled else "disabled"}.')
    return redirect('settings:aggregation')


def suppression_rules(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')

    rules = AlertSuppressionRule.objects.select_related('created_by').all()
    total_suppressed = rules.aggregate(total=Sum('match_count'))['total'] or 0

    if request.method == 'POST':
        form = AlertSuppressionRuleForm(request.POST)
        if form.is_valid():
            rule = form.save(commit=False)
            rule.created_by = request.user
            rule.save()
            _log_setting_change(
                request.user,
                f'Created suppression rule {rule.name}',
                'AlertSuppressionRule',
                rule.id,
                '',
                f'Action={rule.action}',
                request,
            )
            messages.success(request, f'Suppression rule "{rule.name}" created successfully.')
            return redirect('settings:suppression_rules')
    else:
        initial_data = {}
        for param in ['rule_id', 'source_ip', 'destination_ip', 'hostname', 'agent_id', 'username', 'name']:
            if param in request.GET:
                initial_data[param] = request.GET[param]
        form = AlertSuppressionRuleForm(initial=initial_data)

    ctx = {
        'section': 'suppression',
        'rules': rules,
        'form': form,
        'total_rules': rules.count(),
        'active_rules': rules.filter(is_active=True).count(),
        'total_suppressed': total_suppressed,
    }
    return render(request, 'settings_manager/suppression_rules.html', ctx)


def suppression_rule_create(request):
    """Direct endpoint to create a suppression rule (e.g. from 1-click modal on Alert Detail)."""
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')

    if request.method == 'POST':
        form = AlertSuppressionRuleForm(request.POST)
        if form.is_valid():
            rule = form.save(commit=False)
            rule.created_by = request.user
            rule.save()
            _log_setting_change(
                request.user,
                f'Created suppression rule {rule.name}',
                'AlertSuppressionRule',
                rule.id,
                '',
                f'Action={rule.action}',
                request,
            )
            messages.success(request, f'Suppression rule "{rule.name}" activated.')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('settings:suppression_rules')
        else:
            messages.error(request, 'Failed to create suppression rule. Please check required fields.')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
    return redirect('settings:suppression_rules')


def suppression_rule_edit(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    rule = get_object_or_404(AlertSuppressionRule, id=pk)
    if request.method == 'POST':
        form = AlertSuppressionRuleForm(request.POST, instance=rule)
        if form.is_valid():
            form.save()
            _log_setting_change(
                request.user,
                f'Edited suppression rule {rule.name}',
                'AlertSuppressionRule',
                rule.id,
                '',
                'Updated',
                request,
            )
            messages.success(request, f'Suppression rule "{rule.name}" updated.')
            return redirect('settings:suppression_rules')
    else:
        form = AlertSuppressionRuleForm(instance=rule)
    ctx = {'section': 'suppression', 'form': form, 'rule': rule}
    return render(request, 'settings_manager/suppression_rule_edit.html', ctx)


@require_POST
def suppression_rule_toggle(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    rule = get_object_or_404(AlertSuppressionRule, id=pk)
    rule.is_active = not rule.is_active
    rule.save(update_fields=['is_active', 'updated_at'])
    _log_setting_change(
        request.user,
        f'{"Activated" if rule.is_active else "Deactivated"} suppression rule {rule.name}',
        'AlertSuppressionRule',
        rule.id,
        '',
        f'Active={rule.is_active}',
        request,
    )
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok', 'is_active': rule.is_active})
    messages.success(request, f'Rule "{rule.name}" {"activated" if rule.is_active else "deactivated"}.')
    return redirect('settings:suppression_rules')


@require_POST
def suppression_rule_delete(request, pk):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    rule = get_object_or_404(AlertSuppressionRule, id=pk)
    name = rule.name
    rule.delete()
    _log_setting_change(request.user, f'Deleted suppression rule {name}', 'AlertSuppressionRule', pk, '', 'Deleted', request)
    messages.success(request, f'Suppression rule "{name}" deleted.')
    return redirect('settings:suppression_rules')




from django.http import JsonResponse
import json
from alerts.models import Alert
from django.utils import timezone
from datetime import timedelta

def suppression_simulate(request):
    if not _check_settings_access(request.user):
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Create an in-memory rule instance
            rule = AlertSuppressionRule(
                rule_id=data.get('rule_id', ''),
                source_ip=data.get('source_ip', ''),
                destination_ip=data.get('destination_ip', ''),
                hostname=data.get('hostname', ''),
                agent_id=data.get('agent_id', ''),
                username=data.get('username', ''),
                is_regex=data.get('is_regex', False),
                is_active=True
            )
            
            # Fetch alerts from last 30 days (limit to 10000 for performance)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            recent_alerts = Alert.objects.filter(timestamp__gte=thirty_days_ago).values(
                'rule_id', 'source_ip', 'destination_ip', 'hostname', 'agent_id', 'username'
            )[:10000]
            
            match_count = 0
            for alert_data in recent_alerts:
                if rule.matches(alert_data):
                    match_count += 1
            
            total_checked = len(recent_alerts)
            return JsonResponse({
                'status': 'success',
                'match_count': match_count,
                'total_checked': total_checked,
                'days': 30
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)
