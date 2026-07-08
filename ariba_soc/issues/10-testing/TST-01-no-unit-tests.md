# TST-01: No Unit Tests for Any Application

- **Severity**: Critical
- **Priority**: P0 (immediate)
- **Category**: Testing

## Current Problem
Every app's `tests.py` is an empty stub or doesn't exist:
- `accounts/tests.py` — empty (may not exist)
- `alerts/tests.py` — empty stub
- `settings_manager/tests.py` — empty stub
- `wazuh_integration/tests.py` — empty stub
- `audit/tests.py` — empty stub
- `dashboard/tests.py` — empty stub
- `reports/tests.py` — empty stub

There are zero unit tests for models, views, forms, services, or any business logic. This means:
- Refactoring code is high-risk (no regression detection)
- Bugs can be introduced without notice
- The SLA calculation logic has no verification
- The Wazuh API normalization has no test coverage
- RBAC permissions are never validated programmatically

## Expected Behavior
Each app should have comprehensive tests covering at minimum:
- All model methods (`__str__`, `save`, `update_sla`, `calculate_priority`, `has_permission`)
- All form validation (`AlertEditForm.clean`, `UserManagementForm.save`, `ResetPasswordForm`)
- All views (status codes, template used, context variables)
- All services (`update_alert`, `assign_alert`, `normalize_alert`)

## Affected Files
- `*/tests.py` for all 7 apps

## Suggested Fix
Example test for alerts:
```python
# alerts/tests.py
from django.test import TestCase
from django.contrib.auth.models import User
from alerts.models import Alert, AlertSource
from alerts.forms import AlertEditForm
from alerts.services import update_alert, assign_alert
from accounts.models import AnalystProfile

class AlertModelTest(TestCase):
    def setUp(self):
        self.source = AlertSource.objects.create(name='Test', source_type='Wazuh')
        self.alert = Alert.objects.create(
            alert_name='Test Alert',
            severity='Critical',
            alert_time=timezone.now(),
            source=self.source,
        )
    
    def test_update_sla_critical(self):
        self.alert.update_sla()
        self.assertIsNotNone(self.alert.sla_due_at)
        self.assertIn(self.alert.sla_status, ['Within SLA', 'Breached', 'Near SLA breach'])
    
    def test_calculate_priority_critical(self):
        self.assertEqual(self.alert.calculate_priority(), 'Critical')

class AlertFormTest(TestCase):
    def test_close_without_verdict_fails(self):
        form = AlertEditForm(data={'status': 'Closed', 'verdict': 'None'})
        self.assertFalse(form.is_valid())
        self.assertIn('Verdict', str(form.errors))

class WazuhNormalizeTest(TestCase):
    def test_map_level_to_severity(self):
        from wazuh_integration.services import map_level_to_severity
        self.assertEqual(map_level_to_severity(12), 'Critical')
        self.assertEqual(map_level_to_severity(8), 'High')
        self.assertEqual(map_level_to_severity(4), 'Medium')
        self.assertEqual(map_level_to_severity(1), 'Low')
```

## QA Verification
1. Run `python manage.py test` — must show `OK` or `FAILED` with proper failure messages.
2. All written tests must pass.
3. Coverage should be reported if `coverage` is installed.
