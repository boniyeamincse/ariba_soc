# AW-004: SLA Values Hardcoded in Alert Model Instead of Using SLA Settings

- **Severity**: Medium
- **Priority**: P2 (next sprint)
- **Category**: Alert Workflow

## Current Problem
`alerts/models.py:157` defines SLA durations as a hardcoded dictionary:
```python
sla_minutes = {'Critical': 240, 'High': 480, 'Medium': 1440, 'Low': 4320, 'Informational': 4320}
ack_sla = {'Critical': 15, 'High': 30, 'Medium': 120, 'Low': 480, 'Informational': 480}
```
Meanwhile, `settings_manager/models.py:91-105` has a fully functional `SLASettings` model that allows admins to configure per-severity SLA values through the UI. The Alert model's `update_sla()` method (`alerts/models.py:154-170`) uses the hardcoded values and **never reads from `SLASettings`**.

This means:
- Changing SLA values in Settings has no effect on actual alerts
- The SLASettings UI exists but is completely disconnected from the SLA logic
- Administrators cannot adjust SLA thresholds without editing Python code

## Expected Behavior
`Alert.update_sla()` should query `SLASettings` for the alert's severity. If no matching `SLASettings` record exists, fall back to the hardcoded defaults. This ensures the Settings UI has real effect.

## Affected Files
- `alerts/models.py:154-170` (update_sla method)

## Suggested Fix
```python
def update_sla(self):
    if not self.alert_time:
        return
    # Try DB config first
    try:
        sla_config = SLASettings.objects.get(severity=self.severity, is_active=True)
        ack_min = sla_config.acknowledge_minutes
        resolve_min = sla_config.resolve_minutes
        breach_warn = sla_config.breach_warning_minutes
    except SLASettings.DoesNotExist:
        # Fallback defaults
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
```

## QA Verification
1. Change SLA resolve time for Critical from 240 to 60 in Settings → SLA Settings.
2. Create a new Critical alert → SLA must be due in 60 minutes, not 240.
3. Change it back to 240 → next alert must reflect the updated value.
