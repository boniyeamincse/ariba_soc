from django.db import migrations

SEVERITIES = [
    ('Informational', 0, '#6b7280', 480, 4320, 0),
    ('Low', 1, '#22c55e', 480, 4320, 1),
    ('Medium', 2, '#eab308', 120, 1440, 2),
    ('High', 3, '#f97316', 30, 480, 3),
    ('Critical', 4, '#ef4444', 15, 240, 4),
]

STATUSES = [
    ('New', 0, False),
    ('Awaiting Action', 1, False),
    ('In Progress', 2, False),
    ('Pending', 3, False),
    ('Escalated', 4, False),
    ('Closed', 5, True),
    ('Archived', 6, True),
]

VERDICTS = [
    ('None', False),
    ('True Positive', True),
    ('False Positive', True),
    ('Benign Positive', False),
    ('Suspicious', False),
    ('Duplicate', False),
    ('Test Activity', False),
]


def seed(apps, schema_editor):
    SeveritySettings = apps.get_model('settings_manager', 'SeveritySettings')
    StatusSettings = apps.get_model('settings_manager', 'StatusSettings')
    VerdictSettings = apps.get_model('settings_manager', 'VerdictSettings')

    for name, score, color, ack_min, resolve_min, sort_order in SEVERITIES:
        SeveritySettings.objects.get_or_create(name=name, defaults={
            'score': score, 'color': color,
            'sla_acknowledge_minutes': ack_min, 'sla_resolve_minutes': resolve_min,
            'sort_order': sort_order, 'is_active': True,
        })

    for name, sort_order, is_final in STATUSES:
        StatusSettings.objects.get_or_create(name=name, defaults={
            'sort_order': sort_order, 'is_final': is_final, 'is_active': True,
        })

    for name, requires_comment in VERDICTS:
        VerdictSettings.objects.get_or_create(name=name, defaults={
            'requires_comment': requires_comment, 'is_active': True,
        })


def unseed(apps, schema_editor):
    SeveritySettings = apps.get_model('settings_manager', 'SeveritySettings')
    StatusSettings = apps.get_model('settings_manager', 'StatusSettings')
    VerdictSettings = apps.get_model('settings_manager', 'VerdictSettings')
    SeveritySettings.objects.filter(name__in=[s[0] for s in SEVERITIES]).delete()
    StatusSettings.objects.filter(name__in=[s[0] for s in STATUSES]).delete()
    VerdictSettings.objects.filter(name__in=[v[0] for v in VERDICTS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('settings_manager', '0005_reportsetting_last_report_file'),
    ]
    operations = [
        migrations.RunPython(seed, unseed),
    ]
