import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('alerts', '0008_alter_alert_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='alert',
            name='workflow_state',
            field=models.CharField(
                choices=[
                    ('NEW', 'New'), ('QUEUED_L1', 'Queued L1'), ('IN_PROGRESS_L1', 'In Progress L1'),
                    ('PENDING_L2_ACCEPTANCE', 'Pending L2 Acceptance'), ('IN_PROGRESS_L2', 'In Progress L2'),
                    ('RETURNED_TO_L1', 'Returned to L1'), ('PENDING_L3_ACCEPTANCE', 'Pending L3 Acceptance'),
                    ('IN_PROGRESS_L3', 'In Progress L3'), ('RETURNED_TO_L2', 'Returned to L2'),
                    ('INCIDENT', 'Incident'), ('RESOLVED', 'Resolved'), ('CLOSED', 'Closed'),
                    ('REOPENED', 'Reopened'), ('ARCHIVED', 'Archived'),
                ],
                default='NEW', help_text='Normalized workflow state for the L1/L2/L3 escalation engine',
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='alert',
            name='workflow_version',
            field=models.PositiveIntegerField(
                default=1, help_text='Optimistic-concurrency counter; incremented on every state change',
            ),
        ),
        migrations.AddField(
            model_name='alert',
            name='current_owner_team',
            field=models.CharField(
                blank=True, choices=[
                    ('', 'Unassigned'), ('L1', 'L1 Team'), ('L2', 'L2 Team'),
                    ('L3', 'L3 Team'), ('ENG', 'Engineering'), ('MANAGEMENT', 'Management'),
                ],
                default='', help_text='Team that currently owns this alert', max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='alert',
            name='resolved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='alert',
            index=models.Index(fields=['workflow_state'], name='alerts_aler_workflo_ba471e_idx'),
        ),
        migrations.AddIndex(
            model_name='alert',
            index=models.Index(fields=['current_tier'], name='alerts_aler_current_745b37_idx'),
        ),
        migrations.CreateModel(
            name='AlertEscalation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_tier', models.CharField(max_length=20)),
                ('target_tier', models.CharField(max_length=20)),
                ('escalation_reason', models.TextField()),
                ('escalation_status', models.CharField(
                    choices=[
                        ('PENDING', 'Pending'), ('ACCEPTED', 'Accepted'),
                        ('RETURNED', 'Returned'), ('CANCELLED', 'Cancelled'),
                        ('COMPLETED', 'Completed'),
                    ],
                    default='PENDING', max_length=20,
                )),
                ('escalated_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('returned_at', models.DateTimeField(blank=True, null=True)),
                ('return_reason', models.TextField(blank=True)),
                ('sla_due_at', models.DateTimeField(blank=True, null=True)),
                ('alert', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='escalation_records', to='alerts.alert')),
                ('escalated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='escalated_by_records', to=settings.AUTH_USER_MODEL)),
                ('accepted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='escalation_accepted_by', to=settings.AUTH_USER_MODEL)),
                ('returned_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='escalation_returned_by', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-escalated_at'],
            },
        ),
        migrations.AddIndex(
            model_name='alertescalation',
            index=models.Index(fields=['alert', 'escalation_status'], name='alerts_aler_alert_i_2e0315_idx'),
        ),
        migrations.AddIndex(
            model_name='alertescalation',
            index=models.Index(fields=['escalation_status'], name='alerts_aler_escalat_50eaef_idx'),
        ),
        migrations.AddIndex(
            model_name='alertescalation',
            index=models.Index(fields=['target_tier'], name='alerts_aler_target__2684e9_idx'),
        ),
        migrations.CreateModel(
            name='AlertTransition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_state', models.CharField(max_length=30)),
                ('to_state', models.CharField(max_length=30)),
                ('action', models.CharField(max_length=50)),
                ('actor_role', models.CharField(max_length=20)),
                ('reason', models.TextField(blank=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('request_id', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('alert', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transitions', to='alerts.alert')),
                ('actor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='alerttransition',
            index=models.Index(fields=['alert', '-created_at'], name='alerts_aler_alert_i_eea092_idx'),
        ),
        migrations.AddIndex(
            model_name='alerttransition',
            index=models.Index(fields=['action'], name='alerts_aler_action_8a0d69_idx'),
        ),
    ]
