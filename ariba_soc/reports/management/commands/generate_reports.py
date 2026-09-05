from django.core.management.base import BaseCommand
from django.utils import timezone
from settings_manager.models import ReportSetting
from reports.services import is_due, generate_report


class Command(BaseCommand):
    help = 'Generate and send scheduled reports'

    def handle(self, *args, **options):
        now = timezone.now()
        for report in ReportSetting.objects.filter(is_active=True).exclude(schedule='NONE'):
            if not is_due(report, now):
                continue
            errors = []
            relative_path = generate_report(report, now=now, errors=errors)
            if not relative_path:
                for err in errors:
                    self.stderr.write(err)
                self.stdout.write(self.style.WARNING(f'Skipped report {report.name}: generation failed'))
                continue
            self.stdout.write(self.style.SUCCESS(f'Generated report: {report.name} -> {relative_path}'))
