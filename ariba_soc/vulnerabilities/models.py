from django.db import models
from django.contrib.auth.models import User


STATUS_CHOICES = [
    ('NEW', 'New'),
    ('ASSIGNED', 'Assigned'),
    ('IN_PROGRESS', 'In Progress'),
    ('AWAITING_PATCH', 'Awaiting Patch'),
    ('AWAITING_VERIFICATION', 'Awaiting Verification'),
    ('RESOLVED', 'Resolved'),
    ('RISK_ACCEPTED', 'Risk Accepted'),
    ('FALSE_POSITIVE', 'False Positive'),
    ('REOPENED', 'Reopened'),
]

PRIORITY_CHOICES = [
    ('CRITICAL', 'Critical'),
    ('HIGH', 'High'),
    ('MEDIUM', 'Medium'),
    ('LOW', 'Low'),
    ('INFO', 'Informational'),
]

ALLOWED_TRANSITIONS = {
    'NEW': ['ASSIGNED', 'FALSE_POSITIVE', 'RISK_ACCEPTED'],
    'ASSIGNED': ['IN_PROGRESS', 'FALSE_POSITIVE', 'RISK_ACCEPTED'],
    'IN_PROGRESS': ['AWAITING_PATCH', 'AWAITING_VERIFICATION', 'RESOLVED', 'FALSE_POSITIVE', 'RISK_ACCEPTED'],
    'AWAITING_PATCH': ['IN_PROGRESS', 'AWAITING_VERIFICATION', 'RESOLVED', 'REOPENED'],
    'AWAITING_VERIFICATION': ['RESOLVED', 'REOPENED', 'IN_PROGRESS'],
    'RESOLVED': ['REOPENED'],
    'RISK_ACCEPTED': ['REOPENED', 'IN_PROGRESS'],
    'FALSE_POSITIVE': ['NEW', 'REOPENED'],
    'REOPENED': ['ASSIGNED', 'IN_PROGRESS', 'FALSE_POSITIVE'],
}


class VulnerabilityCase(models.Model):
    vulnerability_key = models.CharField(max_length=255, unique=True)
    agent_id = models.CharField(max_length=50)
    agent_name = models.CharField(max_length=255, blank=True)
    cve_id = models.CharField(max_length=50, db_index=True)
    package_name = models.CharField(max_length=255, blank=True)
    installed_version = models.CharField(max_length=100, blank=True)
    vulnerable_version = models.CharField(max_length=100, blank=True)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='NEW')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')

    owner = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='owned_vulnerabilities')
    due_at = models.DateTimeField(null=True, blank=True)
    business_impact = models.TextField(blank=True)
    remediation_note = models.TextField(blank=True)

    risk_accepted = models.BooleanField(default=False)
    risk_acceptance_reason = models.TextField(blank=True)
    risk_accepted_by = models.ForeignKey(User, null=True, blank=True, related_name='accepted_vulnerability_risks', on_delete=models.SET_NULL)
    risk_accepted_at = models.DateTimeField(null=True, blank=True)

    verified_by = models.ForeignKey(User, null=True, blank=True, related_name='verified_vulnerabilities', on_delete=models.SET_NULL)
    verified_at = models.DateTimeField(null=True, blank=True)

    cvss_score = models.FloatField(null=True, blank=True)
    severity = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    reference_url = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cve_id']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['agent_id']),
            models.Index(fields=['-cvss_score']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.cve_id} ({self.vulnerability_key})"

    def can_transition_to(self, new_status):
        return new_status in ALLOWED_TRANSITIONS.get(self.status, [])

    @property
    def primary_reference_url(self):
        if not self.reference_url:
            return ''
        parts = [u.strip() for u in self.reference_url.split(',') if u.strip()]
        return parts[0] if parts else ''

    @property
    def reference_list(self):
        if not self.reference_url:
            return []
        return [u.strip() for u in self.reference_url.split(',') if u.strip()]


class VulnerabilityAuditLog(models.Model):
    vulnerability = models.ForeignKey(VulnerabilityCase, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vulnerability', '-created_at']),
        ]

    def __str__(self):
        return f"{self.action} on {self.vulnerability} by {self.user}"
