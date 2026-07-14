from django import forms
from .models import WazuhConfiguration

class WazuhConfigurationForm(forms.ModelForm):
    class Meta:
        model = WazuhConfiguration
        fields = ['api_type', 'api_url', 'api_username', 'api_password', 'verify_ssl', 'timeout', 'sync_interval_minutes', 'es_index_pattern', 'is_active']
        widgets = {
            'api_type': forms.Select(attrs={'class': 'form-select bg-dark text-light border-secondary'}),
            'api_url': forms.TextInput(attrs={'class': 'form-control bg-dark text-light border-secondary'}),
            'api_username': forms.TextInput(attrs={'class': 'form-control bg-dark text-light border-secondary'}),
            'api_password': forms.PasswordInput(attrs={'class': 'form-control bg-dark text-light border-secondary'}, render_value=True),
            'verify_ssl': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'timeout': forms.NumberInput(attrs={'class': 'form-control bg-dark text-light border-secondary'}),
            'sync_interval_minutes': forms.NumberInput(attrs={'class': 'form-control bg-dark text-light border-secondary'}),
            'es_index_pattern': forms.TextInput(attrs={'class': 'form-control bg-dark text-light border-secondary'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
