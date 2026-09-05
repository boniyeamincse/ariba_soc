from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from settings_manager.models import SLASettings

SEVERITY_CHOICES = [
    ('Informational', 'Informational'),
    ('Low', 'Low'),
    ('Medium', 'Medium'),
    ('High', 'High'),
    ('Critical', 'Critical'),
]

STATUS_CHOICES = [
    ('New', 'New'),
    ('Awaiting Action', 'Awaiting Action'),
    ('In Progress', 'In Progress'),
    ('Pending', 'Pending'),
    ('Escalated to L2', 'Escalated to L2'),
    ('Escalated to L3', 'Escalated to L3'),
    ('Escalated to IR/IT', 'Escalated to IR/IT'),
    ('Escalated to Management', 'Escalated to Management'),
    ('Remediation', 'Remediation'),
    ('Closed', 'Closed'),
    ('Archived', 'Archived'),
]

VERDICT_CHOICES = [
    ('None', 'None'),
    ('True Positive', 'True Positive'),
    ('False Positive', 'False Positive'),
    ('Benign Positive', 'Benign Positive'),
    ('Suspicious', 'Suspicious'),
    ('Duplicate', 'Duplicate'),
    ('Test Activity', 'Test Activity'),
]

PRIORITY_CHOICES = [
    ('Low', 'Low'),
    ('Medium', 'Medium'),
    ('High', 'High'),
    ('Critical', 'Critical'),
]


class AlertSource(models.Model):
    name = models.CharField(max_length=100)
    source_type = models.CharField(max_length=50, default='Wazuh')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Alert Source'
        verbose_name_plural = 'Alert Sources'

    def __str__(self):
        return self.name


class Alert(models.Model):
    wazuh_alert_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    alert_time = models.DateTimeField(default=timezone.now)
    event_time = models.DateTimeField(null=True, blank=True)
    alert_name = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    rule_description = models.TextField(blank=True)
    triage_guide = models.TextField(blank=True)

    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='Medium')
    severity_score = models.IntegerField(default=0)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='New')
    verdict = models.CharField(max_length=20, choices=VERDICT_CHOICES, default='None')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Medium')

    source = models.ForeignKey(AlertSource, on_delete=models.SET_NULL, null=True, blank=True)
    source_name = models.CharField(max_length=100, default='Wazuh')

    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_alerts')
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_by_alerts')
    assigned_at = models.DateTimeField(null=True, blank=True)

    rule_id = models.CharField(max_length=50, blank=True)
    rule_level = models.IntegerField(default=0)
    agent_id = models.CharField(max_length=50, blank=True)
    agent_name = models.CharField(max_length=200, blank=True)
    agent_ip = models.GenericIPAddressField(null=True, blank=True)
    hostname = models.CharField(max_length=200, blank=True)
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    destination_ip = models.GenericIPAddressField(null=True, blank=True)
    username = models.CharField(max_length=200, blank=True)
    process_name = models.CharField(max_length=500, blank=True)
    process_user = models.CharField(max_length=200, blank=True)
    command_line = models.TextField(blank=True)
    target_file = models.CharField(max_length=1000, blank=True)
    file_path = models.CharField(max_length=1000, blank=True)
    file_hash_md5 = models.CharField(max_length=64, blank=True)
    file_hash_sha1 = models.CharField(max_length=64, blank=True)
    file_hash_sha256 = models.CharField(max_length=128, blank=True)
    url = models.URLField(max_length=2000, blank=True)
    mitre_id = models.CharField(max_length=50, blank=True)
    mitre_tactic = models.CharField(max_length=200, blank=True)
    mitre_technique = models.CharField(max_length=200, blank=True)
    full_log = models.TextField(blank=True)
    location = models.CharField(max_length=500, blank=True)
    decoder_name = models.CharField(max_length=200, blank=True)

    alert_fields = models.JSONField(default=dict, blank=True)
    raw_json = models.JSONField(default=dict, blank=True)
    enrichment_data = models.JSONField(default=dict, blank=True)

    analyst_comment = models.TextField(blank=True)
    escalation_reason = models.TextField(blank=True)
    remediation_note = models.TextField(blank=True)
    closure_reason = models.TextField(blank=True)
    root_cause_summary = models.TextField(blank=True)

    sla_due_at = models.DateTimeField(null=True, blank=True)
    sla_status = models.CharField(max_length=20, default='Within SLA')

    acknowledged_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    status_updated_at = models.DateTimeField(auto_now_add=True)

    is_incident_candidate = models.BooleanField(default=False)
    is_escalated = models.BooleanField(default=False)

    current_tier = models.CharField(max_length=20, blank=True, default='', help_text='Current SOC tier handling this alert')
    escalation_status = models.CharField(max_length=30, blank=True, default='', help_text='pending_acceptance, accepted, returned')
    escalated_from_tier = models.CharField(max_length=20, blank=True, default='')
    escalated_to_tier = models.CharField(max_length=20, blank=True, default='')
    accepted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='accepted_alerts')
    accepted_at = models.DateTimeField(null=True, blank=True)
    returned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='returned_alerts')
    returned_at = models.DateTimeField(null=True, blank=True)
    return_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Alert'
        verbose_name_plural = 'Alerts'
        ordering = ['-alert_time']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['severity']),
            models.Index(fields=['verdict']),
            models.Index(fields=['assignee']),
            models.Index(fields=['alert_time']),
            models.Index(fields=['rule_id']),
            models.Index(fields=['hostname']),
            models.Index(fields=['source_ip']),
            models.Index(fields=['wazuh_alert_id']),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.alert_name}"

    def save(self, *args, **kwargs):
        if not self.pk or kwargs.pop('recalc_sla', True):
            self.update_sla()
        if self.status == 'Closed' and not self.closed_at:
            self.closed_at = timezone.now()
        if self.status == 'Archived' and not self.archived_at:
            self.archived_at = timezone.now()
        super().save(*args, **kwargs)

    def update_sla(self):
        if not self.alert_time:
            return
        try:
            sla_config = SLASettings.objects.get(severity=self.severity, is_active=True)
            ack_min = sla_config.acknowledge_minutes
            resolve_min = sla_config.resolve_minutes
            breach_warn = sla_config.breach_warning_minutes
        except SLASettings.DoesNotExist:
            defaults = {'Critical': (15, 240, 30), 'High': (30, 480, 30), 'Medium': (120, 1440, 30),
                         'Low': (480, 4320, 30), 'Informational': (480, 4320, 30)}
            ack_min, resolve_min, breach_warn = defaults.get(self.severity, (120, 1440, 30))

        due = self.alert_time + timezone.timedelta(minutes=resolve_min)
        self.sla_due_at = due
        if self.status in ('Closed', 'Archived') and self.closed_at:
            self.sla_status = 'Breached' if self.closed_at > due else 'Within SLA'
        elif timezone.now() > due:
            self.sla_status = 'Breached'
        elif timezone.now() > (due - timezone.timedelta(minutes=breach_warn)):
            self.sla_status = 'Near SLA breach'

    def calculate_priority(self):
        level = self.rule_level or 0
        if self.severity == 'Critical' or level >= 12:
            return 'Critical'
        elif self.severity == 'High' or level >= 8:
            return 'High'
        elif self.severity == 'Medium' or level >= 4:
            return 'Medium'
        return 'Low'


class AlertComment(models.Model):
    COMMENT_TYPES = [
        ('Analyst Note', 'Analyst Note'),
        ('Escalation Note', 'Escalation Note'),
        ('Remediation Note', 'Remediation Note'),
        ('Closure Note', 'Closure Note'),
        ('Manager Note', 'Manager Note'),
        ('Lessons Learned', 'Lessons Learned'),
    ]
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    comment = models.TextField()
    comment_type = models.CharField(max_length=20, choices=COMMENT_TYPES, default='Analyst Note')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['alert', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user} - {self.comment_type}"


class AlertAuditLog(models.Model):
    ACTIONS = [
        ('Created', 'Created'),
        ('Assigned', 'Assigned'),
        ('Status Changed', 'Status Changed'),
        ('Severity Changed', 'Severity Changed'),
        ('Verdict Changed', 'Verdict Changed'),
        ('Comment Added', 'Comment Added'),
        ('Escalated', 'Escalated'),
        ('Closed', 'Closed'),
        ('Archived', 'Archived'),
        ('Reopened', 'Reopened'),
        ('Priority Changed', 'Priority Changed'),
    ]
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50, choices=ACTIONS)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['alert', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user} {self.action} - {self.alert}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username} - Read: {self.is_read}"
