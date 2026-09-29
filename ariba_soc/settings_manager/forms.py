from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from accounts.models import AnalystProfile, ROLE_CHOICES, TEAM_CHOICES
from .models import (
    AlertSourceSettings, SeveritySettings, StatusSettings, VerdictSettings,
    SLASettings, EscalationRule, NotificationSetting, ReportSetting,
    DashboardSetting, AuditLogSetting, AlarmSetting, AlarmSystemSetting, SystemSetting, IOCEnrichmentSetting,
    AlertAggregationSetting, AlertSuppressionRule
)

class UserManagementForm(UserCreationForm):
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    team = forms.ChoiceField(choices=TEAM_CHOICES, required=False)
    phone = forms.CharField(max_length=20, required=False)
    designation = forms.CharField(max_length=100, required=False)
    is_active = forms.BooleanField(required=False, initial=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['role'].widget.attrs.update({'class': 'form-select form-select-sm'})
        self.fields['team'].widget.attrs.update({'class': 'form-select form-select-sm'})

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            profile, _ = AnalystProfile.objects.get_or_create(user=user)
            profile.role = self.cleaned_data['role']
            profile.team = self.cleaned_data.get('team', '')
            profile.phone = self.cleaned_data.get('phone', '')
            profile.designation = self.cleaned_data.get('designation', '')
            profile.is_active = self.cleaned_data.get('is_active', True)
            profile.save()
        return user

class UserEditForm(forms.ModelForm):
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    team = forms.ChoiceField(choices=TEAM_CHOICES, required=False)
    phone = forms.CharField(max_length=20, required=False)
    designation = forms.CharField(max_length=100, required=False)
    is_active = forms.BooleanField(required=False, initial=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['role'].widget.attrs.update({'class': 'form-select form-select-sm'})
        self.fields['team'].widget.attrs.update({'class': 'form-select form-select-sm'})
        if self.instance and hasattr(self.instance, 'analyst_profile'):
            p = self.instance.analyst_profile
            self.initial['role'] = p.role
            self.initial['team'] = p.team
            self.initial['phone'] = p.phone
            self.initial['designation'] = p.designation
            self.initial['is_active'] = p.is_active

    def save(self, commit=True, files=None):
        user = super().save(commit=False)
        if commit:
            user.save()
            profile, _ = AnalystProfile.objects.get_or_create(user=user)
            profile.role = self.cleaned_data['role']
            profile.team = self.cleaned_data.get('team', '')
            profile.phone = self.cleaned_data.get('phone', '')
            profile.designation = self.cleaned_data.get('designation', '')
            profile.is_active = self.cleaned_data.get('is_active', True)
            if files and 'avatar' in files and files['avatar']:
                profile.avatar = files['avatar']
            profile.save()
        return user

class AnalystProfileForm(forms.ModelForm):
    class Meta:
        model = AnalystProfile
        fields = ['role', 'team', 'phone', 'designation', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({'class': 'form-select form-select-sm' if isinstance(f, (forms.ChoiceField, forms.TypedChoiceField)) else 'form-control form-control-sm'})
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})

class AlertSourceSettingsForm(forms.ModelForm):
    class Meta:
        model = AlertSourceSettings
        fields = ['name', 'source_type', 'description', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})

class SeveritySettingsForm(forms.ModelForm):
    class Meta:
        model = SeveritySettings
        fields = ['name', 'score', 'color', 'sla_acknowledge_minutes', 'sla_resolve_minutes', 'is_active', 'sort_order']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['color'].widget.attrs.update({'type': 'color', 'class': 'form-control form-control-color'})

class StatusSettingsForm(forms.ModelForm):
    class Meta:
        model = StatusSettings
        fields = ['name', 'status_type', 'color', 'sort_order', 'is_final', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['is_final'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['color'].widget.attrs.update({'type': 'color', 'class': 'form-control form-control-color'})

class VerdictSettingsForm(forms.ModelForm):
    class Meta:
        model = VerdictSettings
        fields = ['name', 'verdict_type', 'color', 'requires_comment', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['requires_comment'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['color'].widget.attrs.update({'type': 'color', 'class': 'form-control form-control-color'})

class SLASettingsForm(forms.ModelForm):
    class Meta:
        model = SLASettings
        fields = ['severity', 'acknowledge_minutes', 'resolve_minutes', 'breach_warning_minutes', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})

class EscalationRuleForm(forms.ModelForm):
    class Meta:
        model = EscalationRule
        fields = ['rule_name', 'severity_condition', 'alert_name_keyword', 'wazuh_rule_id', 'escalate_to_role', 'escalate_to_user', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['escalate_to_role'].widget.attrs.update({'class': 'form-select form-select-sm'})
        self.fields['escalate_to_user'].widget.attrs.update({'class': 'form-select form-select-sm'})

class NotificationSettingForm(forms.ModelForm):
    class Meta:
        model = NotificationSetting
        fields = ['name', 'event_type', 'channel', 'recipient_role', 'recipient_user', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['event_type'].widget.attrs.update({'class': 'form-select form-select-sm'})
        self.fields['channel'].widget.attrs.update({'class': 'form-select form-select-sm'})
        self.fields['recipient_role'].widget.attrs.update({'class': 'form-select form-select-sm'})
        self.fields['recipient_user'].widget.attrs.update({'class': 'form-select form-select-sm'})

class ReportSettingForm(forms.ModelForm):
    class Meta:
        model = ReportSetting
        fields = ['name', 'report_type', 'schedule', 'recipient_email', 'export_format', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['report_type'].widget.attrs.update({'class': 'form-select form-select-sm'})
        self.fields['schedule'].widget.attrs.update({'class': 'form-select form-select-sm'})
        self.fields['export_format'].widget.attrs.update({'class': 'form-select form-select-sm'})

class DashboardSettingForm(forms.ModelForm):
    class Meta:
        model = DashboardSetting
        fields = ['role', 'default_page', 'default_date_range', 'auto_refresh_interval', 'show_kpi_cards', 'show_charts', 'show_analyst_workload', 'show_sla_widget']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({'class': 'form-control form-control-sm'})
        for fname in ['show_kpi_cards', 'show_charts', 'show_analyst_workload', 'show_sla_widget']:
            self.fields[fname].widget.attrs.update({'class': 'form-check-input'})
        self.fields['role'].widget.attrs.update({'class': 'form-select form-select-sm'})
        self.fields['default_page'].widget.attrs.update({'class': 'form-select form-select-sm'})
        self.fields['default_date_range'].widget.attrs.update({'class': 'form-select form-select-sm'})

class AuditLogSettingForm(forms.ModelForm):
    class Meta:
        model = AuditLogSetting
        fields = ['action_type', 'log_enabled', 'retention_days', 'is_critical']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['log_enabled'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['is_critical'].widget.attrs.update({'class': 'form-check-input'})

class AlarmSettingForm(forms.ModelForm):
    class Meta:
        model = AlarmSetting
        fields = ['severity', 'is_enabled', 'description', 'sort_order']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['is_enabled'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['severity'].widget.attrs.update({'class': 'form-select form-select-sm'})

class AlarmSystemSettingForm(forms.ModelForm):
    class Meta:
        model = AlarmSystemSetting
        fields = ['is_enabled', 'sound_file']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['is_enabled'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['sound_file'].widget.attrs.update({'class': 'form-control form-control-sm', 'accept': '.mp3,audio/mpeg'})

class AlertAggregationSettingForm(forms.ModelForm):
    class Meta:
        model = AlertAggregationSetting
        fields = [
            'is_enabled', 'window_minutes', 'max_events_per_alert',
            'group_by_rule', 'group_by_source_ip', 'group_by_destination_ip',
            'group_by_agent', 'group_by_username'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            if isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.update({'class': 'form-check-input'})
            else:
                f.widget.attrs.update({'class': 'form-control form-control-sm'})


class AlertSuppressionRuleForm(forms.ModelForm):
    class Meta:
        model = AlertSuppressionRule
        fields = [
            'name', 'action', 'rule_id', 'source_ip', 'destination_ip',
            'hostname', 'agent_id', 'username', 'reason', 'expires_at', 'is_active'
        ]
        widgets = {
            'expires_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control form-control-sm'}),
            'reason': forms.Textarea(attrs={'rows': 2, 'class': 'form-control form-control-sm', 'placeholder': 'Reason for suppression, false positive context or change ticket...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select form-select-sm'})
            elif name not in ['expires_at', 'reason']:
                field.widget.attrs.update({'class': 'form-control form-control-sm'})


class SystemSettingForm(forms.ModelForm):
    class Meta:
        model = SystemSetting
        fields = ['key', 'value', 'description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({'class': 'form-control form-control-sm'})

class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control form-control-sm'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control form-control-sm'}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('new_password') != cleaned.get('confirm_password'):
            raise forms.ValidationError('Passwords do not match.')
        return cleaned

class IOCEnrichmentSettingForm(forms.ModelForm):
    class Meta:
        model = IOCEnrichmentSetting
        fields = ['provider_name', 'api_key', 'is_active', 'auto_enrich']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            if not isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.update({'class': 'form-control form-control-sm'})
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['auto_enrich'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['provider_name'].widget.attrs.update({'class': 'form-select form-select-sm'})
