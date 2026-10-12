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

WORKFLOW_STATE_CHOICES = [
    ('NEW', 'New'),
    ('QUEUED_L1', 'Queued L1'),
    ('IN_PROGRESS_L1', 'In Progress L1'),
    ('PENDING_L2_ACCEPTANCE', 'Pending L2 Acceptance'),
    ('IN_PROGRESS_L2', 'In Progress L2'),
    ('RETURNED_TO_L1', 'Returned to L1'),
    ('PENDING_L3_ACCEPTANCE', 'Pending L3 Acceptance'),
    ('IN_PROGRESS_L3', 'In Progress L3'),
    ('RETURNED_TO_L2', 'Returned to L2'),
    ('INCIDENT', 'Incident'),
    ('RESOLVED', 'Resolved'),
    ('CLOSED', 'Closed'),
    ('REOPENED', 'Reopened'),
    ('ARCHIVED', 'Archived'),
]

ESCALATION_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('ACCEPTED', 'Accepted'),
    ('RETURNED', 'Returned'),
    ('CANCELLED', 'Cancelled'),
    ('COMPLETED', 'Completed'),
]

CURRENT_TIER_CHOICES = [
    ('', 'Unassigned'),
    ('L1', 'L1'),
    ('L2', 'L2'),
    ('L3', 'L3'),
]

CURRENT_OWNER_TEAM_CHOICES = [
    ('', 'Unassigned'),
    ('L1', 'L1 Team'),
    ('L2', 'L2 Team'),
    ('L3', 'L3 Team'),
    ('ENG', 'Engineering'),
    ('MANAGEMENT', 'Management'),
]

ASSET_CRITICALITY_CHOICES = [
    ('LOW', 'Low (0.8x)'),
    ('MEDIUM', 'Medium (1.0x)'),
    ('HIGH', 'High (1.5x)'),
    ('CRITICAL', 'Mission-Critical (2.0x)'),
]

ASSET_TYPE_CHOICES = [
    ('SERVER', 'Server'),
    ('WORKSTATION', 'Workstation / Endpoint'),
    ('DOMAIN_CONTROLLER', 'Domain Controller (DC)'),
    ('DATABASE', 'Database Server'),
    ('PAYMENT_GATEWAY', 'Payment / Financial Gateway'),
    ('FIREWALL', 'Firewall / Gateway'),
    ('CLOUD_INSTANCE', 'Cloud VM / Container'),
    ('OTHER', 'Other Infrastructure'),
]

ENVIRONMENT_CHOICES = [
    ('PROD', 'Production'),
    ('STAGE', 'Staging'),
    ('DEV', 'Development'),
    ('DMZ', 'DMZ / Perimeter'),
    ('CORP', 'Corporate Internal'),
    ('TEST', 'Test / Sandbox'),
]


class Asset(models.Model):
    hostname = models.CharField(max_length=200, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    agent_id = models.CharField(max_length=50, blank=True, db_index=True, help_text='Linked Wazuh Agent ID')
    name = models.CharField(max_length=200, help_text='Friendly business asset name')

    criticality = models.CharField(max_length=20, choices=ASSET_CRITICALITY_CHOICES, default='MEDIUM')
    criticality_multiplier = models.FloatField(default=1.0)
    asset_type = models.CharField(max_length=30, choices=ASSET_TYPE_CHOICES, default='SERVER')
    environment = models.CharField(max_length=20, choices=ENVIRONMENT_CHOICES, default='PROD')

    business_unit = models.CharField(max_length=100, blank=True, help_text='Department or Service Owner')
    owner = models.CharField(max_length=100, blank=True, help_text='Responsible Engineer or Team')
    mac_address = models.CharField(max_length=50, blank=True)
    os_name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    auto_discovered = models.BooleanField(default=False)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Asset'
        verbose_name_plural = 'Assets'
        ordering = ['-criticality_multiplier', 'hostname']
        indexes = [
            models.Index(fields=['hostname']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['agent_id']),
            models.Index(fields=['criticality']),
        ]

    def __str__(self):
        return f"{self.name or self.hostname} ({self.get_criticality_display()})"

    def save(self, *args, **kwargs):
        multipliers = {'LOW': 0.8, 'MEDIUM': 1.0, 'HIGH': 1.5, 'CRITICAL': 2.0}
        if self.criticality in multipliers and (not self.criticality_multiplier or self.criticality_multiplier == 1.0 or kwargs.pop('recalc_multiplier', False)):
            self.criticality_multiplier = multipliers[self.criticality]
        super().save(*args, **kwargs)


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
    assigned_team = models.ForeignKey(
        'accounts.SocTeam',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_alerts',
        help_text='SOC operational team currently responsible for this alert',
    )

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
    compliance_pci = models.CharField(max_length=500, blank=True)
    compliance_gdpr = models.CharField(max_length=500, blank=True)
    compliance_hipaa = models.CharField(max_length=500, blank=True)
    compliance_nist = models.CharField(max_length=500, blank=True)
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

    aggregation_key = models.CharField(max_length=64, blank=True, db_index=True)
    event_count = models.PositiveIntegerField(default=1)
    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)

    asset = models.ForeignKey('Asset', on_delete=models.SET_NULL, null=True, blank=True, related_name='alerts')
    asset_criticality = models.CharField(max_length=20, blank=True, default='')
    risk_score = models.FloatField(default=0.0, help_text='Dynamic Risk Score incorporating asset criticality multiplier')

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

    workflow_state = models.CharField(
        max_length=30, choices=WORKFLOW_STATE_CHOICES, default='NEW',
        help_text='Normalized workflow state for the L1/L2/L3 escalation engine',
    )
    workflow_version = models.PositiveIntegerField(
        default=1,
        help_text='Optimistic-concurrency counter; incremented on every state change',
    )
    current_owner_team = models.CharField(
        max_length=20, choices=CURRENT_OWNER_TEAM_CHOICES, blank=True, default='',
        help_text='Team that currently owns this alert',
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

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
            models.Index(fields=['workflow_state']),
            models.Index(fields=['current_tier']),
            models.Index(fields=['asset']),
            models.Index(fields=['asset_criticality']),
            models.Index(fields=['risk_score']),
            models.Index(fields=['assigned_team']),
            models.Index(fields=['current_owner_team']),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.alert_name}"

    def save(self, *args, **kwargs):
        if self.assigned_team:
            self.current_owner_team = self.assigned_team.tier
        elif self.assignee and not self.assigned_team:
            if hasattr(self.assignee, 'analyst_profile') and self.assignee.analyst_profile.soc_team:
                self.assigned_team = self.assignee.analyst_profile.soc_team
                self.current_owner_team = self.assigned_team.tier
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


class AlertEscalation(models.Model):
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='escalation_records')
    source_tier = models.CharField(max_length=20)
    target_tier = models.CharField(max_length=20)
    escalated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='escalated_by_records')
    escalation_reason = models.TextField()
    escalation_status = models.CharField(max_length=20, choices=ESCALATION_STATUS_CHOICES, default='PENDING')
    escalated_at = models.DateTimeField(default=timezone.now)
    accepted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='escalation_accepted_by')
    accepted_at = models.DateTimeField(null=True, blank=True)
    returned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='escalation_returned_by')
    returned_at = models.DateTimeField(null=True, blank=True)
    return_reason = models.TextField(blank=True)
    sla_due_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-escalated_at']
        indexes = [
            models.Index(fields=['alert', 'escalation_status']),
            models.Index(fields=['escalation_status']),
            models.Index(fields=['target_tier']),
        ]

    def __str__(self):
        return f"Escalation {self.id}: {self.source_tier}→{self.target_tier} [{self.escalation_status}]"


class AlertTransition(models.Model):
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='transitions')
    from_state = models.CharField(max_length=30)
    to_state = models.CharField(max_length=30)
    action = models.CharField(max_length=50)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    actor_role = models.CharField(max_length=20)
    reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    request_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['alert', '-created_at']),
            models.Index(fields=['action']),
        ]

    def __str__(self):
        return f"{self.alert_id}: {self.from_state}→{self.to_state} [{self.action}]"


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
