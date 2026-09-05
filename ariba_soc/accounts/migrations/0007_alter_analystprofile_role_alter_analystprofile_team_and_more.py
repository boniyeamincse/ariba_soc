from django.db import migrations, models


def fix_viewer_permissions(apps, schema_editor):
    RolePermission = apps.get_model('accounts', 'RolePermission')
    try:
        rp = RolePermission.objects.get(role='VIEWER')
        rp.can_change_status = False
        rp.can_change_severity = False
        rp.can_change_verdict = False
        rp.can_close_alert = False
        rp.can_escalate_alert = False
        rp.can_assign_self = False
        rp.can_assign_others = False
        rp.can_archive = False
        rp.can_reassign = False
        rp.can_add_remediation = False
        rp.can_mark_incident = False
        rp.can_export_reports = False
        rp.save()
    except RolePermission.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_seed_l3_role_permission'),
    ]

    operations = [
        migrations.AlterField(
            model_name='analystprofile',
            name='role',
            field=models.CharField(choices=[('L1', 'SOC L1 Analyst'), ('L2', 'SOC L2 Analyst'), ('L3', 'SOC L3 Analyst'), ('SOC_ENG', 'SOC Engineer'), ('SOC_MGR', 'SOC Manager'), ('ADMIN', 'Admin'), ('VIEWER', 'Viewer'), ('MONITOR', 'Monitor')], default='L1', max_length=20),
        ),
        migrations.AlterField(
            model_name='analystprofile',
            name='team',
            field=models.CharField(blank=True, choices=[('L1', 'L1 Team'), ('L2', 'L2 Team'), ('L3', 'L3 Team'), ('ENG', 'Engineering'), ('MANAGEMENT', 'Management')], max_length=20),
        ),
        migrations.AlterField(
            model_name='rolepermission',
            name='role',
            field=models.CharField(choices=[('L1', 'SOC L1 Analyst'), ('L2', 'SOC L2 Analyst'), ('L3', 'SOC L3 Analyst'), ('SOC_ENG', 'SOC Engineer'), ('SOC_MGR', 'SOC Manager'), ('ADMIN', 'Admin'), ('VIEWER', 'Viewer'), ('MONITOR', 'Monitor')], max_length=20, unique=True),
        ),
        migrations.RunPython(fix_viewer_permissions, migrations.RunPython.noop),
    ]
