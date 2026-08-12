from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from accounts.models import AnalystProfile, RolePermission, ROLE_CHOICES, SETTINGS_ALLOWED_ROLES as _FALLBACK_SETTINGS_ROLES
from .models import (
    AlertSourceSettings, SeveritySettings, StatusSettings, VerdictSettings,
    SLASettings, EscalationRule, NotificationSetting, ReportSetting,
    DashboardSetting, AuditLogSetting, SystemSetting, SettingAuditLog,
    IOCEnrichmentSetting
)
from .forms import (
    UserManagementForm, UserEditForm, AnalystProfileForm,
    AlertSourceSettingsForm, SeveritySettingsForm, StatusSettingsForm,
    VerdictSettingsForm, SLASettingsForm, EscalationRuleForm,
    NotificationSettingForm, ReportSettingForm, DashboardSettingForm,
    AuditLogSettingForm, SystemSettingForm, ResetPasswordForm,
    IOCEnrichmentSettingForm
)

def _get_allowed_roles():
    stored = SystemSetting.get_setting('settings_allowed_roles', '')
    if stored:
        return [r.strip() for r in stored.split(',')]
    return _FALLBACK_SETTINGS_ROLES


def _check_settings_access(user):
    if not user.is_authenticated:
        return False
    role = getattr(user.analyst_profile, 'role', '')
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
        'recent_logs': SettingAuditLog.objects.select_related('user').all()[:10],
    }
    return render(request, 'settings_manager/settings_dashboard.html', ctx)

def user_management(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    search = request.GET.get('search', '')
    users = User.objects.select_related('analyst_profile').all()
    if search:
        users = users.filter(Q(username__icontains=search) | Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(email__icontains=search))
    if request.method == 'POST' and 'create' in request.POST:
        form = UserManagementForm(request.POST)
        if form.is_valid():
            user = form.save()
            _log_setting_change(request.user, f'Created user {user.username}', 'User', user.id, '', 'Created', request)
            messages.success(request, f'User {user.username} created.')
            return redirect('settings:user_management')
    else:
        form = UserManagementForm()
    ctx = {'section': 'users', 'users': users, 'form': form, 'search': search}
    return render(request, 'settings_manager/user_management.html', ctx)

def user_edit(request, user_id):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    user = get_object_or_404(User.objects.select_related('analyst_profile'), id=user_id)
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, f'Edited user {user.username}', 'User', user.id, '', 'Updated', request)
            messages.success(request, 'User updated.')
            return redirect('settings:user_management')
    else:
        form = UserEditForm(instance=user)
    ctx = {'section': 'users', 'form': form, 'edit_user': user}
    return render(request, 'settings_manager/user_edit.html', ctx)

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
    roles = RolePermission.objects.all()
    if request.method == 'POST':
        for role_choice, _ in ROLE_CHOICES:
            rp, _ = RolePermission.objects.get_or_create(role=role_choice[0] if isinstance(role_choice, tuple) else role_choice)
            for field in [f.name for f in RolePermission._meta.get_fields() if f.name.startswith('can_')]:
                val = request.POST.get(f'{rp.role}_{field}') == 'on'
                setattr(rp, field, val)
            rp.save()
        _log_setting_change(request.user, 'Updated role permissions', 'RolePermission', 0, '', 'Updated', request)
        messages.success(request, 'Permissions updated.')
        return redirect('settings:role_permission')
    PERMISSION_FIELDS = [
        ('View Alerts', 'can_view_alerts'),
        ('Assign to Self', 'can_assign_self'),
        ('Assign to Others', 'can_assign_others'),
        ('Change Status', 'can_change_status'),
        ('Change Severity', 'can_change_severity'),
        ('Change Verdict', 'can_change_verdict'),
        ('Close Alert', 'can_close_alert'),
        ('Escalate Alert', 'can_escalate_alert'),
        ('View Reports', 'can_view_reports'),
        ('Manage Users', 'can_manage_users'),
        ('Manage Wazuh', 'can_manage_wazuh'),
        ('View Audit Logs', 'can_view_audit_logs'),
        ('Archive', 'can_archive'),
        ('Reassign', 'can_reassign'),
        ('Add Remediation', 'can_add_remediation'),
        ('Mark as Incident', 'can_mark_incident'),
        ('Export Reports', 'can_export_reports'),
    ]
    ctx = {'section': 'roles', 'roles': roles, 'role_choices': ROLE_CHOICES, 'permissions': PERMISSION_FIELDS}
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
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    config = None
    try:
        from wazuh_integration.models import WazuhConfiguration
        config = WazuhConfiguration.objects.first()
    except Exception:
        pass
    if request.method == 'POST':
        from wazuh_integration.forms import WazuhConfigurationForm
        form = WazuhConfigurationForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, 'Updated Wazuh API settings', 'WazuhConfiguration', config.id if config else 0, '', 'Updated', request)
            messages.success(request, 'Wazuh API settings saved.')
            return redirect('settings:wazuh_api')
    else:
        from wazuh_integration.forms import WazuhConfigurationForm
        form = WazuhConfigurationForm(instance=config)
    ctx = {'section': 'wazuh_api', 'form': form, 'config': config}
    return render(request, 'settings_manager/wazuh_api_settings.html', ctx)

def alert_source_settings(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    search = request.GET.get('search', '')
    sources = AlertSourceSettings.objects.all()
    if search:
        sources = sources.filter(name__icontains=search)
    if request.method == 'POST':
        form = AlertSourceSettingsForm(request.POST)
        if form.is_valid():
            form.save()
            _log_setting_change(request.user, 'Created alert source', 'AlertSourceSettings', 0, '', form.cleaned_data['name'], request)
            messages.success(request, 'Source created.')
            return redirect('settings:alert_sources')
    else:
        form = AlertSourceSettingsForm()
    ctx = {'section': 'sources', 'sources': sources, 'form': form, 'search': search}
    return render(request, 'settings_manager/alert_source_settings.html', ctx)

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

def severity_toggle(request, pk):
    obj = get_object_or_404(SeveritySettings, id=pk)
    obj.is_active = not obj.is_active
    obj.save()
    messages.success(request, f'Severity {"activated" if obj.is_active else "deactivated"}.')
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

def status_toggle(request, pk):
    obj = get_object_or_404(StatusSettings, id=pk)
    obj.is_active = not obj.is_active
    obj.save()
    messages.success(request, f'Status {"activated" if obj.is_active else "deactivated"}.')
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

def verdict_toggle(request, pk):
    obj = get_object_or_404(VerdictSettings, id=pk)
    obj.is_active = not obj.is_active
    obj.save()
    messages.success(request, f'Verdict {"activated" if obj.is_active else "deactivated"}.')
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

def sla_toggle(request, pk):
    obj = get_object_or_404(SLASettings, id=pk)
    obj.is_active = not obj.is_active
    obj.save()
    messages.success(request, f'SLA {"activated" if obj.is_active else "deactivated"}.')
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

def escalation_toggle(request, pk):
    obj = get_object_or_404(EscalationRule, id=pk)
    obj.is_active = not obj.is_active
    obj.save()
    messages.success(request, f'Rule {"activated" if obj.is_active else "deactivated"}.')
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

def notification_toggle(request, pk):
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

def report_toggle(request, pk):
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

def audit_log_toggle(request, pk):
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
