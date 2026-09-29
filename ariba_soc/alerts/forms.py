from django import forms
from django.contrib.auth.models import User
from settings_manager.models import SeveritySettings, StatusSettings, VerdictSettings
from .models import Alert, AlertComment, SEVERITY_CHOICES, STATUS_CHOICES, VERDICT_CHOICES

class AlertEditForm(forms.ModelForm):
    analyst_comment = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}), required=False)
    escalation_reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}), required=False)
    remediation_note = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}), required=False)
    closure_reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}), required=False)
    lessons_learned = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}), required=False)
    severity_change_reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}), required=False)

    class Meta:
        model = Alert
        fields = ['assignee', 'status', 'severity', 'verdict', 'priority', 'analyst_comment', 'escalation_reason', 'remediation_note', 'closure_reason']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['assignee'].queryset = User.objects.filter(is_active=True).select_related('analyst_profile')
        self.fields['assignee'].widget.attrs.update({'class': 'form-select'})

        self.fields['severity'].choices = list(
            SeveritySettings.objects.filter(is_active=True).order_by('sort_order').values_list('name', 'name')
        ) or SEVERITY_CHOICES
        self.fields['status'].choices = list(
            StatusSettings.objects.filter(is_active=True).order_by('sort_order').values_list('name', 'name')
        ) or STATUS_CHOICES
        self.fields['verdict'].choices = list(
            VerdictSettings.objects.filter(is_active=True).order_by('name').values_list('name', 'name')
        ) or VERDICT_CHOICES

        self.fields['status'].widget.attrs.update({'class': 'form-select'})
        self.fields['severity'].widget.attrs.update({'class': 'form-select'})
        self.fields['verdict'].widget.attrs.update({'class': 'form-select'})
        self.fields['priority'].widget.attrs.update({'class': 'form-select'})
        self.initial_verdict = self.instance.verdict if self.instance else 'None'

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get('status')
        verdict = cleaned.get('verdict')
        comment = cleaned.get('analyst_comment')
        escalation = cleaned.get('escalation_reason')

        status_is_final = StatusSettings.objects.filter(name=status, is_final=True).exists()
        verdict_requires_comment = VerdictSettings.objects.filter(name=verdict, requires_comment=True).exists()

        if status_is_final and verdict in ('None', ''):
            raise forms.ValidationError('Verdict cannot be None when closing an alert.')
        if verdict_requires_comment and not comment:
            raise forms.ValidationError(f'Analyst comment is required for {verdict} verdict.')
        if status and status.startswith('Escalated') and not escalation:
            raise forms.ValidationError('Escalation reason is required when escalating.')
        return cleaned


class AlertCommentForm(forms.ModelForm):
    class Meta:
        model = AlertComment
        fields = ['comment', 'comment_type']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comment'].widget.attrs.update({'rows': 3, 'class': 'form-control', 'placeholder': 'Add your comment...'})
        self.fields['comment_type'].widget.attrs.update({'class': 'form-select'})


class AlertQuickAssignForm(forms.Form):
    alert_id = forms.IntegerField(widget=forms.HiddenInput())


class AssetForm(forms.ModelForm):
    class Meta:
        from .models import Asset
        model = Asset
        fields = [
            'name', 'hostname', 'ip_address', 'agent_id',
            'criticality', 'criticality_multiplier', 'asset_type',
            'environment', 'business_unit', 'owner', 'mac_address',
            'os_name', 'description', 'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Primary Active Directory DC'}),
            'hostname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. dc01.corp.local'}),
            'ip_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 10.0.1.10'}),
            'agent_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 001'}),
            'criticality': forms.Select(attrs={'class': 'form-select'}),
            'criticality_multiplier': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'asset_type': forms.Select(attrs={'class': 'form-select'}),
            'environment': forms.Select(attrs={'class': 'form-select'}),
            'business_unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Core Banking / IT'}),
            'owner': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Infrastructure Team'}),
            'mac_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00:1A:2B:3C:4D:5E'}),
            'os_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Windows Server 2022'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Asset function and notes...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

