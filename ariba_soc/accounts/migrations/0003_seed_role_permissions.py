from django.db import migrations

# Sensible SOC-hierarchy defaults. Without this, no RolePermission rows
# exist at all, and RolePermission.has_permission() returns False for
# every role (including ADMIN) regardless of the model's field defaults --
# every check_perm()-gated action (escalate/close/archive/change severity
# etc.) 403s for everyone.
ROLE_PERMISSIONS = {
    'VIEWER': dict(
        can_view_alerts=True, can_view_reports=True,
    ),
    'L1': dict(
        can_view_alerts=True, can_assign_self=True, can_change_status=True,
        can_change_verdict=True, can_escalate_alert=True, can_view_reports=True,
    ),
    'L2': dict(
        can_view_alerts=True, can_assign_self=True, can_change_status=True,
        can_change_severity=True, can_change_verdict=True, can_close_alert=True,
        can_escalate_alert=True, can_view_reports=True, can_reassign=True,
        can_add_remediation=True, can_mark_incident=True, can_export_reports=True,
    ),
    'SOC_ENG': dict(
        can_view_alerts=True, can_assign_self=True, can_change_status=True,
        can_change_severity=True, can_change_verdict=True, can_close_alert=True,
        can_escalate_alert=True, can_view_reports=True, can_manage_wazuh=True,
        can_archive=True, can_reassign=True, can_add_remediation=True,
        can_mark_incident=True, can_export_reports=True,
    ),
    'SOC_MGR': dict(
        can_view_alerts=True, can_assign_self=True, can_assign_others=True,
        can_change_status=True, can_change_severity=True, can_change_verdict=True,
        can_close_alert=True, can_escalate_alert=True, can_view_reports=True,
        can_manage_users=True, can_view_audit_logs=True, can_archive=True,
        can_reassign=True, can_add_remediation=True, can_mark_incident=True,
        can_export_reports=True,
    ),
    'ADMIN': dict(
        can_view_alerts=True, can_assign_self=True, can_assign_others=True,
        can_change_status=True, can_change_severity=True, can_change_verdict=True,
        can_close_alert=True, can_escalate_alert=True, can_view_reports=True,
        can_manage_users=True, can_manage_wazuh=True, can_view_audit_logs=True,
        can_archive=True, can_reassign=True, can_add_remediation=True,
        can_mark_incident=True, can_export_reports=True,
    ),
}


def seed(apps, schema_editor):
    RolePermission = apps.get_model('accounts', 'RolePermission')
    for role, perms in ROLE_PERMISSIONS.items():
        RolePermission.objects.get_or_create(role=role, defaults=perms)


def unseed(apps, schema_editor):
    RolePermission = apps.get_model('accounts', 'RolePermission')
    RolePermission.objects.filter(role__in=ROLE_PERMISSIONS.keys()).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_analystprofile_avatar'),
    ]
    operations = [
        migrations.RunPython(seed, unseed),
    ]
