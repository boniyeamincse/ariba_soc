from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

ROLE_CHOICES = [
    ('L1', 'SOC L1 Analyst'),
    ('L2', 'SOC L2 Analyst'),
    ('L3', 'SOC L3 Analyst'),
    ('SOC_ENG', 'SOC Engineer'),
    ('SOC_MGR', 'SOC Manager'),
    ('ADMIN', 'Admin'),
    ('VIEWER', 'Viewer'),
    ('MONITOR', 'Monitor'),
]

SETTINGS_ALLOWED_ROLES = ['SOC_MGR', 'SOC_ENG', 'ADMIN']
WAZUH_ALLOWED_ROLES = ['ADMIN', 'SOC_ENG', 'SOC_MGR', 'L1', 'L2', 'L3']

TEAM_CHOICES = [
    ('L1', 'L1 Team'),
    ('L2', 'L2 Team'),
    ('L3', 'L3 Team'),
    ('ENG', 'Engineering'),
    ('MANAGEMENT', 'Management'),
]


class SocTeam(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    TIER_CHOICES = [
        ('L1', 'Tier 1 - Triage & Initial Response'),
        ('L2', 'Tier 2 - Advanced Investigation & IR'),
        ('L3', 'Tier 3 - Threat Hunting & Forensics'),
        ('ENG', 'Detection Engineering & Wazuh'),
        ('MGMT', 'SOC Management & Governance'),
    ]
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='L1')

    lead = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='led_teams'
    )

    SHIFT_CHOICES = [
        ('24x7', '24x7 Dedicated'),
        ('MORNING', 'Morning Shift (08:00 - 16:00)'),
        ('EVENING', 'Evening Shift (16:00 - 00:00)'),
        ('NIGHT', 'Night Shift (00:00 - 08:00)'),
        ('GENERAL', 'Standard Business Hours (09:00 - 18:00)'),
    ]
    shift_type = models.CharField(max_length=20, choices=SHIFT_CHOICES, default='GENERAL')
    shift_start_time = models.TimeField(null=True, blank=True)
    shift_end_time = models.TimeField(null=True, blank=True)

    notification_email = models.EmailField(blank=True)
    webhook_url = models.URLField(blank=True, help_text='Slack/Teams/Webhook endpoint for team alerts')

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['tier', 'name']
        verbose_name = 'SOC Team'
        verbose_name_plural = 'SOC Teams'

    def __str__(self):
        return f"{self.name} ({self.get_tier_display()})"


class AnalystProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='analyst_profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='L1')
    team = models.CharField(max_length=20, choices=TEAM_CHOICES, blank=True)
    soc_team = models.ForeignKey(
        SocTeam, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='members',
        help_text='Dynamic SOC Team assigned to this analyst'
    )
    phone = models.CharField(max_length=20, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Analyst Profile'
        verbose_name_plural = 'Analyst Profiles'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"

    def has_permission(self, perm):
        return RolePermission.has_permission(self.role, perm)


class RolePermission(models.Model):
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=True)
    can_view_alerts = models.BooleanField(default=True)
    can_assign_self = models.BooleanField(default=True)
    can_assign_others = models.BooleanField(default=False)
    can_change_status = models.BooleanField(default=True)
    can_change_severity = models.BooleanField(default=False)
    can_change_verdict = models.BooleanField(default=True)
    can_close_alert = models.BooleanField(default=False)
    can_escalate_alert = models.BooleanField(default=True)
    can_view_reports = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)
    can_manage_wazuh = models.BooleanField(default=False)
    can_view_audit_logs = models.BooleanField(default=False)
    can_archive = models.BooleanField(default=False)
    can_reassign = models.BooleanField(default=False)
    can_add_remediation = models.BooleanField(default=False)
    can_mark_incident = models.BooleanField(default=False)
    can_export_reports = models.BooleanField(default=False)
    can_use_basic_hunting = models.BooleanField(default=True)
    can_use_advanced_hunting = models.BooleanField(default=False)
    can_view_incidents = models.BooleanField(default=True)
    can_create_incident = models.BooleanField(default=False)
    can_assign_incident = models.BooleanField(default=False)
    can_manage_incident = models.BooleanField(default=False)
    can_close_incident = models.BooleanField(default=False)
    can_reopen_incident = models.BooleanField(default=False)
    can_link_incident_alerts = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Role Permission'
        verbose_name_plural = 'Role Permissions'

    def __str__(self):
        return f"Permissions for {self.get_role_display()}"

    @staticmethod
    def has_permission(role, perm):
        try:
            rp = RolePermission.objects.get(role=role)
            return getattr(rp, perm, False)
        except RolePermission.DoesNotExist:
            return False


@receiver(post_save, sender=User)
def create_analyst_profile(sender, instance, created, **kwargs):
    if created:
        AnalystProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_analyst_profile(sender, instance, **kwargs):
    if hasattr(instance, 'analyst_profile'):
        instance.analyst_profile.save()


SHIFT_TYPE_CHOICES = [
    ('24x7', '24/7 Follow-the-Sun'),
    ('MORNING', 'Morning Shift (06:00 - 14:00)'),
    ('EVENING', 'Evening Shift (14:00 - 22:00)'),
    ('NIGHT', 'Night Shift (22:00 - 06:00)'),
    ('GENERAL', 'General / Business Hours (09:00 - 18:00)'),
]

HANDOVER_STATUS_CHOICES = [
    ('DRAFT', 'Draft'),
    ('SUBMITTED', 'Submitted - Pending Acknowledgment'),
    ('ACKNOWLEDGED', 'Acknowledged & Handed Over'),
]


class ShiftHandoverLog(models.Model):
    outgoing_team = models.ForeignKey(
        SocTeam, on_delete=models.CASCADE, related_name='handovers_sent',
        help_text="Team currently completing duty"
    )
    incoming_team = models.ForeignKey(
        SocTeam, on_delete=models.CASCADE, related_name='handovers_received',
        help_text="Team assuming operational responsibility"
    )
    outgoing_lead = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='handovers_submitted',
        help_text="Lead/analyst submitting the handover"
    )
    incoming_lead = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='handovers_acknowledged', help_text="Incoming Lead accepting the handover"
    )
    shift_date = models.DateField(default=timezone.now)
    shift_type = models.CharField(max_length=20, choices=SHIFT_TYPE_CHOICES, default='MORNING')
    status = models.CharField(max_length=20, choices=HANDOVER_STATUS_CHOICES, default='SUBMITTED')

    # Shift Activity Metrics Snapshot
    alerts_ingested_count = models.IntegerField(default=0)
    alerts_closed_count = models.IntegerField(default=0)
    escalations_count = models.IntegerField(default=0)
    open_critical_count = models.IntegerField(default=0)

    # Operational Handover Briefing Notes
    active_incidents_summary = models.TextField(blank=True, help_text="Summary of ongoing high/critical investigations")
    containment_actions_taken = models.TextField(blank=True, help_text="Active containment, SOAR blocks, or isolated assets")
    infrastructure_health_notes = models.TextField(blank=True, help_text="Wazuh, sensor, or pipeline operational notes")
    handover_notes = models.TextField(help_text="Priority action items and handover briefing for incoming shift")

    # Acknowledgment Tracking
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledgment_comment = models.TextField(blank=True, help_text="Notes/confirmations from incoming lead")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Shift Handover Log'
        verbose_name_plural = 'Shift Handover Logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"Handover #{self.id}: {self.outgoing_team.name} → {self.incoming_team.name} ({self.shift_date})"
