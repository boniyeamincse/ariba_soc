from django import forms
from .models import Incident, IncidentNote


class IncidentCreateForm(forms.Form):
    title = forms.CharField(max_length=500, widget=forms.TextInput(attrs={'class': 'form-control'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    severity = forms.ChoiceField(choices=Incident.SEVERITY_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    priority = forms.ChoiceField(choices=Incident.PRIORITY_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    business_unit = forms.CharField(required=False, max_length=200, widget=forms.TextInput(attrs={'class': 'form-control'}))
    affected_service = forms.CharField(required=False, max_length=200, widget=forms.TextInput(attrs={'class': 'form-control'}))
    business_impact = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}))
    response_team = forms.CharField(required=False, max_length=200, widget=forms.TextInput(attrs={'class': 'form-control'}))
    declaration_reason = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}))


class IncidentFilterForm(forms.Form):
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search...'}))
    status = forms.ChoiceField(required=False, choices=[('', 'All')] + Incident.STATUS_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    severity = forms.ChoiceField(required=False, choices=[('', 'All')] + Incident.SEVERITY_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    priority = forms.ChoiceField(required=False, choices=[('', 'All')] + Incident.PRIORITY_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))


class NoteForm(forms.Form):
    note_type = forms.ChoiceField(choices=IncidentNote.NOTE_TYPES, widget=forms.Select(attrs={'class': 'form-select'}))
    note = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))


class TransitionForm(forms.Form):
    evidence = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    version = forms.IntegerField(widget=forms.HiddenInput())
