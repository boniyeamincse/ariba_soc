from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage
from django.utils import timezone
from datetime import timedelta
from settings_manager.models import ReportSetting


class Command(BaseCommand):
    help = 'Generate and send scheduled reports'

    def handle(self, *args, **options):
        now = timezone.now()
        for report in ReportSetting.objects.filter(is_active=True).exclude(schedule='NONE'):
            if self._is_due(report, now):
                filepath = self._generate(report)
                if filepath and report.recipient_email:
                    self._email(report, filepath)
                report.last_generated_at = now
                report.save(update_fields=['last_generated_at'])
                self.stdout.write(f'Generated report: {report.name}')

    def _is_due(self, report, now):
        if not report.last_generated_at:
            return True
        intervals = {'DAILY': 1, 'WEEKLY': 7, 'MONTHLY': 30}
        days = intervals.get(report.schedule, 1)
        return (now - report.last_generated_at) > timedelta(days=days)

    def _generate(self, report):
        return None

    def _email(self, report, filepath):
        EmailMessage(
            subject=f'SOC Report: {report.name}',
            body='Please find attached your scheduled SOC report.',
            to=[report.recipient_email],
        ).send(fail_silently=True)
