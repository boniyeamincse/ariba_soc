from django import forms
from .services.query_validator import TIME_RANGE_PRESETS, L1_MAX_RESULTS, ADVANCED_MAX_RESULTS


class LiveSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        max_length=2000,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search query (e.g., failed login, rule.description:ssh)',
            'id': 'search-query',
        }),
    )
    time_range = forms.ChoiceField(
        required=False,
        choices=[
            ('15m', 'Last 15 minutes'),
            ('1h', 'Last 1 hour'),
            ('6h', 'Last 6 hours'),
            ('24h', 'Last 24 hours'),
            ('7d', 'Last 7 days'),
            ('30d', 'Last 30 days'),
            ('custom', 'Custom range'),
        ],
        initial='1h',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'time-range'}),
    )
    start_time = forms.CharField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local',
            'id': 'start-time',
        }),
    )
    end_time = forms.CharField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local',
            'id': 'end-time',
        }),
    )
    agent_id = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Agent ID'}),
    )
    agent_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Agent name'}),
    )
    hostname = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Hostname'}),
    )
    source_ip = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Source IP'}),
    )
    destination_ip = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Destination IP'}),
    )
    username = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
    )
    rule_id = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Rule ID'}),
    )
    rule_level = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0-15'}),
    )
    severity = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All severities'),
            ('Critical', 'Critical'),
            ('High', 'High'),
            ('Medium', 'Medium'),
            ('Low', 'Low'),
            ('Informational', 'Informational'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    mitre_tactic = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'MITRE tactic'}),
    )
    mitre_technique = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'MITRE technique'}),
    )
    groups = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Event groups (comma-separated)'}),
    )
    limit = forms.IntegerField(
        required=False,
        initial=100,
        min_value=1,
        max_value=500,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'result-limit'}),
    )

    def clean_limit(self):
        limit = self.cleaned_data.get('limit')
        if limit is None:
            return 100
        return min(max(1, limit), 500)

    def get_filters(self):
        data = self.cleaned_data.copy()
        data = {k: v for k, v in data.items() if v is not None and v != ''}
        return data
