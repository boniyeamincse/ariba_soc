from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('alerts', '0006_alert_enrichment_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='alert',
            name='current_tier',
            field=models.CharField(blank=True, default='', help_text='Current SOC tier handling this alert', max_length=20),
        ),
        migrations.AddField(
            model_name='alert',
            name='escalation_status',
            field=models.CharField(blank=True, default='', help_text='pending_acceptance, accepted, returned', max_length=30),
        ),
        migrations.AddField(
            model_name='alert',
            name='escalated_from_tier',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='alert',
            name='escalated_to_tier',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='alert',
            name='accepted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='accepted_alerts', to='auth.user'),
        ),
        migrations.AddField(
            model_name='alert',
            name='accepted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='alert',
            name='returned_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='returned_alerts', to='auth.user'),
        ),
        migrations.AddField(
            model_name='alert',
            name='returned_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='alert',
            name='return_reason',
            field=models.TextField(blank=True),
        ),
    ]
