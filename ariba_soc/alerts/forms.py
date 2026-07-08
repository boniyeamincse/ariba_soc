from django import forms
from django.contrib.auth.models import User
from .models import Alert, AlertComment, SEVERITY_CHOICES, STATUS_CHOICES, VERDICT_CHOICES

class AlertEditForm(forms.ModelForm):
    analyst_comment = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}), required=False)
    escalation_reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}), required=False)
    remediation_note = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}), required=False)
    closure_reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}), required=False)
    severity_change_reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}), required=False)

    class Meta:
        model = Alert
        fields = ['assignee', 'status', 'severity', 'verdict', 'priority', 'analyst_comment', 'escalation_reason', 'remediation_note', 'closure_reason']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['assignee'].queryset = User.objects.filter(is_active=True).select_related('analyst_profile')
        self.fields['assignee'].widget.attrs.update({'class': 'form-select'})
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

        if status == 'Closed' and verdict in ('None', ''):
            raise forms.ValidationError('Verdict cannot be None when closing an alert.')
        if verdict == 'True Positive' and not comment:
            raise forms.ValidationError('Analyst comment is required for True Positive verdict.')
        if verdict == 'False Positive' and not comment:
            raise forms.ValidationError('Comment/reason is required for False Positive verdict.')
        if status == 'Escalated' and not escalation:
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
