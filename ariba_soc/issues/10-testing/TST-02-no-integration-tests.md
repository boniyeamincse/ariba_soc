# TST-02: No Integration or End-to-End Tests

- **Severity**: High
- **Priority**: P1 (this sprint)
- **Category**: Testing

## Current Problem
Beyond missing unit tests, there are no integration tests that verify:
- Complete alert lifecycle: Create → Assign → Update → Escalate → Close → Reopen
- Alert board drag-and-drop status changes
- Wazuh sync → alert creation flow
- Settings CRUD operations
- User creation → profile creation signal
- Role permission matrix save → query → enforce

Without integration tests, cross-component bugs (e.g., the escalation rules that exist but are never executed) cannot be caught automatically.

## Expected Behavior
Integration tests should be written using Django's `TestCase` with `Client` to simulate full HTTP requests and verify the complete request-response cycle.

## Affected Files
- `alerts/tests.py` (needs integration test cases)
- `settings_manager/tests.py` (needs integration test cases)
- `accounts/tests.py` (needs signal test cases)

## Suggested Fix
```python
class AlertWorkflowIntegrationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='analyst', password='test1234')
        AnalystProfile.objects.create(user=self.user, role='L1')
        self.client.login(username='analyst', password='test1234')
    
    def test_full_alert_lifecycle(self):
        # Create
        alert = Alert.objects.create(alert_name='Test', severity='High')
        
        # Assign
        response = self.client.post(f'/alerts/{alert.id}/assign/', {'assignee_id': self.user.id})
        self.assertRedirects(response, ...)
        alert.refresh_from_db()
        self.assertEqual(alert.assignee, self.user)
        
        # Update severity
        response = self.client.post(f'/alerts/{alert.id}/edit/', {
            'severity': 'Critical', 'status': 'In Progress', 'verdict': 'Suspicious'
        })
        alert.refresh_from_db()
        self.assertEqual(alert.severity, 'Critical')
        
        # Close
        response = self.client.post(f'/alerts/{alert.id}/close/', {
            'verdict': 'True Positive',
            'closure_comment': 'Confirmed threat.'
        })
        alert.refresh_from_db()
        self.assertEqual(alert.status, 'Closed')
```

## QA Verification
1. Run `python manage.py test alerts.tests.AlertWorkflowIntegrationTest`.
2. All lifecycle steps must pass without human intervention.
3. The database state after each step must match expectations.
