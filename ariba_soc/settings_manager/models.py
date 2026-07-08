from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from accounts.models import ROLE_CHOICES

class SettingAuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=200)
    model_name = models.CharField(max_length=100)
    object_id = models.IntegerField(null=True, blank=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.action}"

class AlertSourceSettings(models.Model):
    name = models.CharField(max_length=100, unique=True)
    source_type = models.CharField(max_length=50, default='Wazuh')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Alert Source'
        verbose_name_plural = 'Alert Sources'

    def __str__(self):
        return self.name

class SeveritySettings(models.Model):
    name = models.CharField(max_length=50, unique=True)
    score = models.IntegerField(default=0)
    color = models.CharField(max_length=20, default='#6b7280')
    sla_acknowledge_minutes = models.IntegerField(default=15)
    sla_resolve_minutes = models.IntegerField(default=60)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Severity Setting'
        verbose_name_plural = 'Severity Settings'
        ordering = ['sort_order']

    def __str__(self):
        return self.name

class StatusSettings(models.Model):
    name = models.CharField(max_length=50, unique=True)
    status_type = models.CharField(max_length=30, blank=True)
    color = models.CharField(max_length=20, default='#6b7280')
    sort_order = models.IntegerField(default=0)
    is_final = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Status Setting'
        verbose_name_plural = 'Status Settings'
        ordering = ['sort_order']

    def __str__(self):
        return self.name

class VerdictSettings(models.Model):
    name = models.CharField(max_length=50, unique=True)
    verdict_type = models.CharField(max_length=30, blank=True)
    color = models.CharField(max_length=20, default='#6b7280')
    requires_comment = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Verdict Setting'
        verbose_name_plural = 'Verdict Settings'
        ordering = ['name']

    def __str__(self):
        return self.name

class SLASettings(models.Model):
    severity = models.CharField(max_length=50, unique=True)
    acknowledge_minutes = models.IntegerField()
    resolve_minutes = models.IntegerField()
    breach_warning_minutes = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'SLA Setting'
        verbose_name_plural = 'SLA Settings'

    def __str__(self):
        return f"SLA for {self.severity}"

class EscalationRule(models.Model):
    rule_name = models.CharField(max_length=200)
    severity_condition = models.CharField(max_length=50, blank=True)
    alert_name_keyword = models.CharField(max_length=200, blank=True)
    wazuh_rule_id = models.CharField(max_length=50, blank=True)
    escalate_to_role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True)
    escalate_to_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Escalation Rule'
        verbose_name_plural = 'Escalation Rules'

    def __str__(self):
        return self.rule_name

class NotificationSetting(models.Model):
    NOTIFICATION_EVENTS = [
        ('NEW_CRITICAL', 'New Critical Alert'),
        ('ALERT_ASSIGNED', 'Alert Assigned'),
        ('ALERT_ESCALATED', 'Alert Escalated'),
        ('SLA_BREACH', 'SLA Breach'),
        ('ALERT_CLOSED', 'Alert Closed'),
        ('TP_CONFIRMED', 'True Positive Confirmed'),
    ]
    CHANNELS = [
        ('EMAIL', 'Email'),
        ('DASHBOARD', 'Dashboard'),
        ('TEAMS', 'Microsoft Teams'),
    ]
    name = models.CharField(max_length=200)
    event_type = models.CharField(max_length=50, choices=NOTIFICATION_EVENTS)
    channel = models.CharField(max_length=20, choices=CHANNELS, default='DASHBOARD')
    recipient_role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True)
    recipient_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Notification Setting'
        verbose_name_plural = 'Notification Settings'

    def __str__(self):
        return self.name

class ReportSetting(models.Model):
    REPORT_TYPES = [
        ('DAILY', 'Daily SOC Report'),
        ('WEEKLY', 'Weekly SOC Report'),
        ('MONTHLY', 'Monthly SOC Report'),
        ('ANALYST', 'Analyst Performance'),
        ('SLA', 'SLA Breach Report'),
        ('TP', 'True Positive Report'),
        ('FP', 'False Positive Report'),
    ]
    EXPORT_FORMATS = [
        ('PDF', 'PDF'),
        ('CSV', 'CSV'),
        ('EXCEL', 'Excel'),
    ]
    SCHEDULES = [
        ('NONE', 'No Schedule'),
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
    ]
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    schedule = models.CharField(max_length=20, choices=SCHEDULES, default='NONE')
    recipient_email = models.EmailField(blank=True)
    export_format = models.CharField(max_length=20, choices=EXPORT_FORMATS, default='CSV')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Report Setting'
        verbose_name_plural = 'Report Settings'

    def __str__(self):
        return self.name

class DashboardSetting(models.Model):
    PAGE_CHOICES = [
        ('alerts:table', 'Alert Table'),
        ('alerts:board', 'Alert Board'),
        ('alerts:my_alerts', 'My Alerts'),
        ('dashboard:home', 'Management Dashboard'),
    ]
    DATE_RANGES = [
        ('today', 'Today'),
        ('7d', 'Last 7 Days'),
        ('30d', 'Last 30 Days'),
        ('90d', 'Last 90 Days'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=True)
    default_page = models.CharField(max_length=100, choices=PAGE_CHOICES, default='alerts:table')
    default_date_range = models.CharField(max_length=20, choices=DATE_RANGES, default='7d')
    auto_refresh_interval = models.IntegerField(default=30, help_text='Seconds')
    show_kpi_cards = models.BooleanField(default=True)
    show_charts = models.BooleanField(default=True)
    show_analyst_workload = models.BooleanField(default=True)
    show_sla_widget = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Dashboard Setting'
        verbose_name_plural = 'Dashboard Settings'

    def __str__(self):
        return f"Dashboard config for {self.get_role_display()}"

class AuditLogSetting(models.Model):
    action_type = models.CharField(max_length=100, unique=True)
    log_enabled = models.BooleanField(default=True)
    retention_days = models.IntegerField(default=365)
    is_critical = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Audit Log Setting'
        verbose_name_plural = 'Audit Log Settings'

    def __str__(self):
        return self.action_type

class SystemSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(blank=True)
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'

    def __str__(self):
        return self.key

    @staticmethod
    def get_setting(key, default=''):
        try:
            return SystemSetting.objects.get(key=key).value
        except SystemSetting.DoesNotExist:
            return default
