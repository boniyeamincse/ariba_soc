# SEC-015: No incident playbook support

**Severity:** Low  
**Priority:** P3  
**Category:** Missing Feature  
**Status:** Open  
**File:** `ariba_soc/alerts/`

## Current Problem
No incident playbook support. `is_incident_candidate` flag exists but is never set automatically or used in workflow.

## Expected Behavior
- Playbook templates for common incidents
- Auto-assignment based on playbook
- Response procedure tracking

## Affected Files
- `ariba_soc/alerts/models.py`
- `ariba_soc/alerts/views.py`

## Suggested Fix
```python
# models.py
class Playbook(models.Model):
    name = models.CharField(max_length=200)
    trigger_rule = models.JSONField()  # Conditions to auto-assign
    steps = models.JSONField()  # Response steps
    severity = models.CharField(max_length=20)
    
class IncidentPlaybook(models.Model):
    alert = models.OneToOneField(Alert, on_delete=models.CASCADE)
    playbook = models.ForeignKey(Playbook, on_delete=models.CASCADE)
    current_step = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default='active')
```

## QA Verification
- Create playbook for "Brute Force" alerts
- New brute force alert triggers playbook
- Analyst follows playbook steps
