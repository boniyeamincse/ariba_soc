from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, FileExtensionValidator
from config.fields import EncryptedCharField
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
        indexes = [
            models.Index(fields=['-created_at']),
        ]

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
        ('YEARLY', 'Yearly'),
    ]
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    schedule = models.CharField(max_length=20, choices=SCHEDULES, default='NONE')
    recipient_email = models.EmailField(blank=True)
    export_format = models.CharField(max_length=20, choices=EXPORT_FORMATS, default='CSV')
    is_active = models.BooleanField(default=True)
    last_generated_at = models.DateTimeField(null=True, blank=True)
    last_report_file = models.CharField(max_length=500, blank=True)
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

class AlarmSetting(models.Model):
    SEVERITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Critical', 'Critical'),
    ]

    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, unique=True)
    is_enabled = models.BooleanField(default=True)
    description = models.CharField(max_length=255, blank=True)
    sort_order = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Alarm Setting'
        verbose_name_plural = 'Alarm Settings'
        ordering = ['sort_order', 'severity']

    def __str__(self):
        return f"Alarm for {self.severity}"

    @classmethod
    def system_enabled(cls):
        return AlarmSystemSetting.load().is_enabled

    @classmethod
    def severity_enabled(cls, severity):
        if not cls.system_enabled():
            return False
        try:
            return cls.objects.get(severity=severity).is_enabled
        except cls.DoesNotExist:
            return False

class AlarmSystemSetting(models.Model):
    is_enabled = models.BooleanField(default=True)
    enable_audio = models.BooleanField(default=True)
    enable_visual = models.BooleanField(default=True)
    volume = models.IntegerField(default=100)
    sound_file = models.FileField(
        upload_to='alarm_sounds/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['mp3'])],
    )
    is_active = models.BooleanField(default=False)
    active_alert_id = models.IntegerField(null=True, blank=True)
    active_alert_name = models.CharField(max_length=500, blank=True)
    active_severity = models.CharField(max_length=20, blank=True)
    active_message = models.CharField(max_length=255, blank=True)
    triggered_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Alarm System Setting'
        verbose_name_plural = 'Alarm System Setting'

    def __str__(self):
        return 'Alarm System Control'

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @classmethod
    def get_sound_url(cls):
        obj = cls.load()
        return obj.sound_file.url if obj.sound_file else ''

    @classmethod
    def activate_for_alert(cls, alert, message=''):
        from django.utils import timezone

        obj = cls.load()
        if not obj.is_enabled:
            return obj
        obj.is_active = True
        obj.active_alert_id = alert.id
        obj.active_alert_name = alert.alert_name
        obj.active_severity = alert.severity
        obj.active_message = message or f'Alarm triggered for {alert.alert_name}'
        obj.triggered_at = timezone.now()
        obj.acknowledged_at = None
        obj.save(update_fields=[
            'is_active', 'active_alert_id', 'active_alert_name', 'active_severity',
            'active_message', 'triggered_at', 'acknowledged_at', 'updated_at'
        ])
        return obj

    @classmethod
    def stop_alarm(cls):
        from django.utils import timezone

        obj = cls.load()
        obj.is_active = False
        obj.active_alert_id = None
        obj.active_alert_name = ''
        obj.active_severity = ''
        obj.active_message = ''
        obj.acknowledged_at = timezone.now()
        obj.save(update_fields=[
            'is_active', 'active_alert_id', 'active_alert_name', 'active_severity',
            'active_message', 'acknowledged_at', 'updated_at'
        ])
        return obj

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

    @staticmethod
    def set_setting(key, value, description=''):
        defaults = {'value': str(value)}
        if description:
            defaults['description'] = description
        obj, _ = SystemSetting.objects.update_or_create(key=key, defaults=defaults)
        return obj

class IOCEnrichmentSetting(models.Model):
    PROVIDER_CHOICES = [
        ('VirusTotal', 'VirusTotal'),
        ('IPInfo', 'IPInfo'),
        ('AbuseIPDB', 'AbuseIPDB'),
        ('OTX', 'AlienVault OTX'),
    ]
    provider_name = models.CharField(max_length=50, choices=PROVIDER_CHOICES, unique=True)
    api_key = EncryptedCharField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    auto_enrich = models.BooleanField(default=True, help_text="Automatically enrich new alerts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'IOC Enrichment Setting'
        verbose_name_plural = 'IOC Enrichment Settings'

    def __str__(self):
        return self.provider_name


class AlertAggregationSetting(models.Model):
    is_enabled = models.BooleanField(default=True, help_text='Enable or disable alert aggregation')
    window_minutes = models.PositiveIntegerField(default=15, help_text='Time window in minutes to group duplicate alerts')
    group_by_rule = models.BooleanField(default=True, help_text='Group alerts by Rule ID')
    group_by_source_ip = models.BooleanField(default=True, help_text='Group alerts by Source IP')
    group_by_destination_ip = models.BooleanField(default=False, help_text='Group alerts by Destination IP')
    group_by_agent = models.BooleanField(default=True, help_text='Group alerts by Agent ID / Hostname')
    group_by_username = models.BooleanField(default=False, help_text='Group alerts by Username')
    max_events_per_alert = models.PositiveIntegerField(default=500, help_text='Max events before creating a new alert')
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Alert Aggregation Setting'
        verbose_name_plural = 'Alert Aggregation Setting'

    def __str__(self):
        return f"Alert Aggregation ({'Enabled' if self.is_enabled else 'Disabled'}, {self.window_minutes}m)"

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def generate_aggregation_key(self, data_or_rule_id=None, source_ip=None, destination_ip=None, agent_id=None, hostname=None, username=None, **kwargs):
        if not self.is_enabled:
            return ''
        import hashlib

        if isinstance(data_or_rule_id, dict):
            rule_id = str(data_or_rule_id.get('rule_id') or '')
            source_ip = str(data_or_rule_id.get('source_ip') or '')
            destination_ip = str(data_or_rule_id.get('destination_ip') or '')
            agent_id = str(data_or_rule_id.get('agent_id') or '')
            hostname = str(data_or_rule_id.get('hostname') or '')
            username = str(data_or_rule_id.get('username') or '')
        else:
            rule_id = str(data_or_rule_id or '')
            source_ip = str(source_ip or '')
            destination_ip = str(destination_ip or '')
            agent_id = str(agent_id or '')
            hostname = str(hostname or '')
            username = str(username or '')

        parts = []
        if self.group_by_rule and rule_id:
            parts.append(f"rule:{rule_id}")
        if self.group_by_source_ip and source_ip:
            parts.append(f"src:{source_ip}")
        if self.group_by_destination_ip and destination_ip:
            parts.append(f"dst:{destination_ip}")
        if self.group_by_agent and (agent_id or hostname):
            parts.append(f"agent:{agent_id or hostname}")
        if self.group_by_username and username:
            parts.append(f"user:{username}")
        if not parts:
            return ''
        raw = '|'.join(parts)
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()


class AlertSuppressionRule(models.Model):
    ACTION_CHOICES = [
        ('AUTO_CLOSE', 'Auto-Close as False Positive'),
        ('DROP', 'Drop (Do not ingest alert)'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved & Active'),
        ('REJECTED', 'Rejected'),
    ]

    name = models.CharField(max_length=200, help_text="Rule name / description")
    rule_id = models.CharField(max_length=50, blank=True, help_text="Rule ID to suppress (e.g. 5710, or blank for any)")
    source_ip = models.CharField(max_length=100, blank=True, help_text="Source IP or CIDR (e.g. 10.0.0.0/24)")
    destination_ip = models.CharField(max_length=100, blank=True, help_text="Destination IP or CIDR")
    hostname = models.CharField(max_length=255, blank=True, help_text="Hostname to match (supports regex if enabled)")
    agent_id = models.CharField(max_length=50, blank=True, help_text="Agent ID to match")
    username = models.CharField(max_length=150, blank=True, help_text="Username to match (supports regex if enabled)")
    is_regex = models.BooleanField(default=False, help_text="Evaluate text fields (Hostname, Username) as Regular Expressions")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default='AUTO_CLOSE', help_text="Action to take when alert matches")
    reason = models.TextField(blank=True, help_text="Business justification / False positive rationale / Change ticket")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='suppression_rules')
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Optional expiration date/time")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='APPROVED', help_text="Approval status (Phase 5)")
    is_active = models.BooleanField(default=True, help_text="Enable or disable this suppression rule")
    match_count = models.PositiveIntegerField(default=0, help_text="Number of alerts suppressed by this rule")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Alert Suppression Rule'
        verbose_name_plural = 'Alert Suppression Rules'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_action_display()})"

    @property
    def is_expired(self):
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False

    def matches(self, alert_data):
        if not self.is_active or self.is_expired:
            return False

        has_criteria = False

        if self.rule_id:
            has_criteria = True
            if str(alert_data.get('rule_id') or '') != str(self.rule_id):
                return False

        if self.agent_id:
            has_criteria = True
            if str(alert_data.get('agent_id') or '') != str(self.agent_id):
                return False

        import re
        import ipaddress

        def match_ip(rule_ip, target_ip):
            if not rule_ip: return True
            if not target_ip: return False
            try:
                if '/' in rule_ip:
                    return ipaddress.ip_address(target_ip) in ipaddress.ip_network(rule_ip)
                return rule_ip == target_ip
            except ValueError:
                return rule_ip == target_ip

        if self.source_ip:
            has_criteria = True
            if not match_ip(self.source_ip, alert_data.get('source_ip', '')):
                return False
        
        if self.destination_ip:
            has_criteria = True
            if not match_ip(self.destination_ip, alert_data.get('destination_ip', '')):
                return False

        def match_text(rule_text, target_text):
            if not rule_text: return True
            if not target_text: return False
            if self.is_regex:
                try:
                    return bool(re.search(rule_text, target_text))
                except re.error:
                    return False
            return rule_text.lower() in target_text.lower()

        if self.username:
            has_criteria = True
            if not match_text(self.username, alert_data.get('username', '')):
                return False
                
        if self.hostname:
            has_criteria = True
            if not match_text(self.hostname, alert_data.get('hostname', '')):
                return False

        return has_criteria
