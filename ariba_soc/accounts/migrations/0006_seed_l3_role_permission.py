from django.db import migrations


def seed_l3(apps, schema_editor):
    RolePermission = apps.get_model('accounts', 'RolePermission')
    RolePermission.objects.get_or_create(
        role='L3',
        defaults=dict(
            can_view_alerts=True, can_assign_self=True, can_change_status=True,
            can_change_severity=True, can_change_verdict=True, can_close_alert=True,
            can_escalate_alert=True, can_view_reports=True, can_reassign=True,
            can_add_remediation=True, can_mark_incident=True, can_export_reports=True,
        ),
    )


def unseed_l3(apps, schema_editor):
    RolePermission = apps.get_model('accounts', 'RolePermission')
    RolePermission.objects.filter(role='L3').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0005_seed_monitor_role_permission'),
    ]
    operations = [
        migrations.RunPython(seed_l3, unseed_l3),
    ]
