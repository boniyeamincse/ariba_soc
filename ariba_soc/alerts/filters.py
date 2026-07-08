import django_filters
from django import forms
from .models import Alert

class AlertFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method='search_filter', label='Search', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by name, host, user, IP, rule ID...'}))
    severity = django_filters.MultipleChoiceFilter(choices=Alert.SEVERITY_CHOICES, widget=forms.SelectMultiple(attrs={'class': 'form-select'}))
    status = django_filters.MultipleChoiceFilter(choices=Alert.STATUS_CHOICES, widget=forms.SelectMultiple(attrs={'class': 'form-select'}))
    verdict = django_filters.MultipleChoiceFilter(choices=Alert.VERDICT_CHOICES, widget=forms.SelectMultiple(attrs={'class': 'form-select'}))
    assignee = django_filters.ModelChoiceFilter(queryset=None, widget=forms.Select(attrs={'class': 'form-select'}))
    date_from = django_filters.DateTimeFilter(field_name='alert_time', lookup_expr='gte', widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}))
    date_to = django_filters.DateTimeFilter(field_name='alert_time', lookup_expr='lte', widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}))

    class Meta:
        model = Alert
        fields = ['severity', 'status', 'verdict', 'assignee', 'priority']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters['assignee'].field.queryset = Alert.objects.exclude(assignee__isnull=True).values_list('assignee', flat=True).distinct()

    def search_filter(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(alert_name__icontains=value) |
            Q(hostname__icontains=value) |
            Q(username__icontains=value) |
            Q(source_ip__icontains=value) |
            Q(destination_ip__icontains=value) |
            Q(rule_id__icontains=value) |
            Q(agent_name__icontains=value) |
            Q(process_name__icontains=value)
        )
