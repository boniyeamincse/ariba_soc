from django import forms
from .models import VulnerabilityCase, STATUS_CHOICES, PRIORITY_CHOICES


class VulnerabilityFilterForm(forms.Form):
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search CVE, package...'}))
    status = forms.ChoiceField(required=False, choices=[('', 'All Statuses')] + STATUS_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    priority = forms.ChoiceField(required=False, choices=[('', 'All Priorities')] + PRIORITY_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    cve_id = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CVE ID'}))
    agent_id = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Agent ID'}))


class AssignForm(forms.Form):
    owner = forms.CharField(widget=forms.HiddenInput())


class RemediationNoteForm(forms.Form):
    remediation_note = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), required=True)


class RiskAcceptanceForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), required=True)


class ReopenForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}), required=False)
