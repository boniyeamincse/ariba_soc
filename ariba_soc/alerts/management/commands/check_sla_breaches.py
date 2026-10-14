"""Periodic SLA-breach worker.

Recomputes SLA state for every open alert, dispatches notifications the first
time an alert breaches, and (optionally) auto-escalates breached Critical/High
alerts one tier up. Idempotent: re-running never re-notifies an alert because
``sla_breach_notified_at`` is set once.

Intended to be run from the scheduler container every few minutes.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from alerts import workflow
from alerts.models import Alert, TERMINAL_STATUSES
from alerts.services import notify_sla_breach
from settings_manager.models import SystemSetting

AUTO_ESCALATE_SEVERITIES = ('Critical', 'High')


class Command(BaseCommand):
    help = 'Recompute SLAs for open alerts, notify on new breaches, and optionally auto-escalate.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--auto-escalate', action='store_true',
            help='Force auto-escalation of breached Critical/High alerts (overrides the setting).',
        )
        parser.add_argument(
            '--backfill', action='store_true',
            help='Mark all currently-breached alerts as already notified WITHOUT sending '
                 'notifications. Use once on first deploy to avoid a notification storm '
                 'from historical backlog.',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report what would happen without writing any changes.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        backfill = options['backfill']
        configured = SystemSetting.get_setting('sla_auto_escalate', 'false')
        auto_escalate = options['auto_escalate'] or str(configured).lower() == 'true'

        qs = Alert.objects.exclude(status__in=TERMINAL_STATUSES).select_related('assignee')

        scanned = breached = notified = escalated = backfilled = 0
        for alert in qs.iterator():
            scanned += 1
            alert.update_sla()
            if alert.sla_status != 'Breached':
                if not dry_run:
                    alert.save(
                        update_fields=[
                            'sla_status', 'sla_due_at', 'sla_ack_due_at', 'sla_breach_phase',
                        ],
                        recalc_sla=False,
                    )
                continue

            breached += 1
            newly_breached = alert.sla_breach_notified_at is None

            if dry_run:
                if newly_breached:
                    notified += 1
                self.stdout.write(
                    f'  [dry-run] {alert.id} {alert.alert_name!r} '
                    f'severity={alert.severity} phase={alert.sla_breach_phase} '
                    f'new={"yes" if newly_breached else "no"}'
                )
                continue

            if newly_breached and backfill:
                alert.sla_breach_notified_at = timezone.now()
                backfilled += 1
            elif newly_breached:
                notify_sla_breach(alert)
                alert.sla_breach_notified_at = timezone.now()
                notified += 1

                if (
                    auto_escalate
                    and not alert.is_escalated
                    and alert.severity in AUTO_ESCALATE_SEVERITIES
                    and (alert.current_tier or 'L1') in ('L1', 'L2')
                ):
                    if workflow.system_auto_escalate(
                        alert, reason='SLA breach auto-escalation'
                    ):
                        escalated += 1

            alert.save(
                update_fields=[
                    'sla_status', 'sla_due_at', 'sla_ack_due_at',
                    'sla_breach_phase', 'sla_breach_notified_at',
                ],
                recalc_sla=False,
            )

        prefix = '[dry-run] ' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'{prefix}SLA check complete: scanned={scanned} breached={breached} '
            f'notified={notified} backfilled={backfilled} escalated={escalated}'
        ))
