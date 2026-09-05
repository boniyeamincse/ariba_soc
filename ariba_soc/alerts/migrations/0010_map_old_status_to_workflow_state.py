from django.db import migrations


STATUS_TO_WORKFLOW = {
    'New': 'NEW',
    'Awaiting Action': 'QUEUED_L1',
    'In Progress': 'IN_PROGRESS_L1',
    'Pending': 'IN_PROGRESS_L1',
    'Escalated to L2': 'PENDING_L2_ACCEPTANCE',
    'Escalated to L3': 'PENDING_L3_ACCEPTANCE',
    'Escalated to IR/IT': 'PENDING_L3_ACCEPTANCE',
    'Escalated to Management': 'PENDING_L3_ACCEPTANCE',
    'Remediation': 'IN_PROGRESS_L2',
    'Closed': 'CLOSED',
    'Archived': 'ARCHIVED',
}

STATUS_TO_TIER = {
    'New': 'L1',
    'Awaiting Action': 'L1',
    'In Progress': 'L1',
    'Pending': 'L1',
    'Escalated to L2': 'L2',
    'Escalated to L3': 'L3',
    'Escalated to IR/IT': 'L3',
    'Escalated to Management': 'L3',
    'Remediation': 'L2',
    'Closed': '',
    'Archived': '',
}


def forwards(apps, schema_editor):
    Alert = apps.get_model('alerts', 'Alert')
    for alert in Alert.objects.all():
        old_status = alert.status or 'New'
        alert.workflow_state = STATUS_TO_WORKFLOW.get(old_status, 'NEW')
        alert.current_tier = STATUS_TO_TIER.get(old_status, 'L1')
        alert.workflow_version = 1
        alert.save(update_fields=['workflow_state', 'current_tier', 'workflow_version'])


def backwards(apps, schema_editor):
    Alert = apps.get_model('alerts', 'Alert')
    WORKFLOW_TO_STATUS = {v: k for k, v in STATUS_TO_WORKFLOW.items()}
    for alert in Alert.objects.all():
        alert.status = WORKFLOW_TO_STATUS.get(alert.workflow_state, 'New')
        alert.save(update_fields=['status'])


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0009_workflow_fields_and_models'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
