from django.db import migrations

# MONITOR is restricted to the dashboard by accounts.middleware.
# MonitorAccessMiddleware -- no alert/report/admin action is reachable
# regardless of these flags, so everything stays False here.


def seed(apps, schema_editor):
    RolePermission = apps.get_model('accounts', 'RolePermission')
    RolePermission.objects.get_or_create(role='MONITOR', defaults=dict(
        can_view_alerts=False, can_assign_self=False, can_assign_others=False,
        can_change_status=False, can_change_severity=False, can_change_verdict=False,
        can_close_alert=False, can_escalate_alert=False, can_view_reports=False,
        can_manage_users=False, can_manage_wazuh=False, can_view_audit_logs=False,
        can_archive=False, can_reassign=False, can_add_remediation=False,
        can_mark_incident=False, can_export_reports=False,
    ))


def unseed(apps, schema_editor):
    RolePermission = apps.get_model('accounts', 'RolePermission')
    RolePermission.objects.filter(role='MONITOR').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0004_alter_analystprofile_role_alter_rolepermission_role'),
    ]
    operations = [
        migrations.RunPython(seed, unseed),
    ]
