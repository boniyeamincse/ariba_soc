from django.db import migrations


def populate_hunting_permissions(apps, schema_editor):
    RolePermission = apps.get_model('accounts', 'RolePermission')
    advanced_roles = ['L2', 'L3', 'SOC_ENG', 'SOC_MGR', 'ADMIN']
    RolePermission.objects.filter(role__in=advanced_roles).update(can_use_advanced_hunting=True)


def reverse_populate(apps, schema_editor):
    RolePermission = apps.get_model('accounts', 'RolePermission')
    RolePermission.objects.all().update(can_use_advanced_hunting=False)


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0008_add_hunting_permissions'),
    ]

    operations = [
        migrations.RunPython(populate_hunting_permissions, reverse_populate),
    ]
