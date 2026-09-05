from django.db import migrations

NEW_STATUSES = [
    ('Escalated to L2', 4, False),
    ('Escalated to IR/IT', 5, False),
    ('Escalated to Management', 6, False),
    ('Remediation', 7, False),
]


def forwards(apps, schema_editor):
    StatusSettings = apps.get_model('settings_manager', 'StatusSettings')

    StatusSettings.objects.filter(name='Escalated').delete()

    for name, sort_order, is_final in NEW_STATUSES:
        StatusSettings.objects.get_or_create(name=name, defaults={
            'sort_order': sort_order, 'is_final': is_final, 'is_active': True,
        })

    StatusSettings.objects.filter(name='Closed').update(sort_order=8)
    StatusSettings.objects.filter(name='Archived').update(sort_order=9)


def backwards(apps, schema_editor):
    StatusSettings = apps.get_model('settings_manager', 'StatusSettings')
    StatusSettings.objects.filter(name__in=[n for n, _, _ in NEW_STATUSES]).delete()
    StatusSettings.objects.get_or_create(name='Escalated', defaults={
        'sort_order': 4, 'is_final': False, 'is_active': True,
    })
    StatusSettings.objects.filter(name='Closed').update(sort_order=5)
    StatusSettings.objects.filter(name='Archived').update(sort_order=6)


class Migration(migrations.Migration):
    dependencies = [
        ('settings_manager', '0006_seed_severity_status_verdict'),
    ]
    operations = [
        migrations.RunPython(forwards, backwards),
    ]
