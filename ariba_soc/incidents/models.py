import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Incident(models.Model):
    STATUS_CHOICES = [
        ('NEW', 'New'),
        ('CONFIRMED', 'Confirmed'),
        ('INVESTIGATING', 'Investigating'),
        ('CONTAINMENT', 'Containment'),
        ('ERADICATION', 'Eradication'),
        ('RECOVERY', 'Recovery'),
        ('MONITORING', 'Monitoring'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
        ('REOPENED', 'Reopened'),
    ]

    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    incident_number = models.CharField(max_length=30, unique=True, db_index=True)
    title = models.CharField(max_length=500)
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='NEW')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')

    owner = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='owned_incidents')
    response_team = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_incidents')

    business_unit = models.CharField(max_length=200, blank=True)
    affected_service = models.CharField(max_length=200, blank=True)
    business_impact = models.TextField(blank=True)
    detection_source = models.CharField(max_length=200, blank=True)
    declaration_reason = models.TextField(blank=True)
    current_tier = models.CharField(max_length=20, blank=True, default='L2')

    version = models.IntegerField(default=1)

    detected_at = models.DateTimeField(null=True, blank=True)
    declared_at = models.DateTimeField(null=True, blank=True)
    contained_at = models.DateTimeField(null=True, blank=True)
    eradicated_at = models.DateTimeField(null=True, blank=True)
    recovered_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['severity']),
            models.Index(fields=['owner']),
            models.Index(fields=['-detected_at']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.incident_number} - {self.title}"

    @staticmethod
    def generate_incident_number():
        from django.db.models import Max
        import datetime
        year = datetime.datetime.now().year
        prefix = f'INC-{year}-'
        last = Incident.objects.filter(
            incident_number__startswith=prefix
        ).aggregate(max_num=Max('incident_number'))['max_num']
        if last:
            try:
                num = int(last.split('-')[-1]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = 1
        return f'{prefix}{num:06d}'


class IncidentAlert(models.Model):
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='linked_alerts')
    alert = models.ForeignKey('alerts.Alert', on_delete=models.PROTECT, related_name='incident_links')
    linked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    link_reason = models.TextField(blank=True)
    is_primary = models.BooleanField(default=False)
    linked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('incident', 'alert')
        ordering = ['-is_primary', '-linked_at']

    def __str__(self):
        return f"{self.alert} → {self.incident}"

    def clean(self):
        if self.is_primary:
            existing = IncidentAlert.objects.filter(
                incident=self.incident, is_primary=True
            ).exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError('Only one primary alert is allowed per incident')


class IncidentTimeline(models.Model):
    EVENT_TYPE_CHOICES = [
        ('CREATED', 'Created'),
        ('ALERT_LINKED', 'Alert Linked'),
        ('ALERT_UNLINKED', 'Alert Unlinked'),
        ('ASSIGNED', 'Assigned'),
        ('STATUS_CHANGED', 'Status Changed'),
        ('SEVERITY_CHANGED', 'Severity Changed'),
        ('NOTE_ADDED', 'Note Added'),
        ('CONTAINED', 'Contained'),
        ('ERADICATED', 'Eradicated'),
        ('RECOVERED', 'Recovered'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
        ('REOPENED', 'Reopened'),
    ]

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='timeline')
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    actor_role = models.CharField(max_length=20, blank=True)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    from_value = models.CharField(max_length=500, blank=True)
    to_value = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    request_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Incident timelines'

    def __str__(self):
        return f"{self.event_type} on {self.incident}"


class IncidentNote(models.Model):
    NOTE_TYPES = [
        ('INVESTIGATION', 'Investigation'),
        ('CONTAINMENT', 'Containment'),
        ('ERADICATION', 'Eradication'),
        ('RECOVERY', 'Recovery'),
        ('MANAGEMENT', 'Management'),
        ('LESSON_LEARNED', 'Lesson Learned'),
    ]

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='notes')
    note_type = models.CharField(max_length=20, choices=NOTE_TYPES, default='INVESTIGATION')
    note = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.note_type} note on {self.incident}"
