# RP-003: Scheduled Report Settings Defined But No Delivery Mechanism

- **Severity**: Medium
- **Priority**: P2 (next sprint)
- **Category**: Reports

## Current Problem
`settings_manager/models.py:155-190` defines `ReportSetting` with fields for `report_type`, `schedule` (DAILY, WEEKLY, MONTHLY), `recipient_email`, and `export_format`. The settings UI allows creating these records. However, **no scheduled task or management command reads these settings and generates reports on schedule**.

The `reports/views.py` only provides manual on-demand exports triggered by user clicks. Scheduled report generation, email delivery, and report archiving are all unimplemented.

## Expected Behavior
A management command (e.g., `python manage.py generate_scheduled_reports`) should:
1. Read all `ReportSetting` records where `is_active=True` and `schedule != 'NONE'`
2. Check if a report is due based on the schedule and last-generated timestamp
3. Generate the report in the specified format
4. Email it to the configured `recipient_email`
5. Update `last_generated_at` on the report setting
6. Be callable from cron / Celery Beat

## Affected Files
- `settings_manager/management/commands/generate_reports.py` (needs to be created)

## Suggested Fix
```python
from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage
from settings_manager.models import ReportSetting
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Generate and send scheduled reports'

    def handle(self, *args, **options):
        for report in ReportSetting.objects.filter(is_active=True).exclude(schedule='NONE'):
            if self._is_due(report):
                filepath = self._generate(report)
                self._email(report, filepath)
                report.last_generated_at = timezone.now()
                report.save()
    
    def _is_due(self, report):
        if not report.last_generated_at:
            return True
        intervals = {'DAILY': 1, 'WEEKLY': 7, 'MONTHLY': 30}
        days = intervals.get(report.schedule, 1)
        return (timezone.now() - report.last_generated_at) > timedelta(days=days)
    
    def _generate(self, report):
        # Generate report based on report.report_type
        ...
    
    def _email(self, report, filepath):
        EmailMessage(
            subject=f'SOC Report: {report.name}',
            body='Please find attached your scheduled SOC report.',
            to=[report.recipient_email],
        ).attach_file(filepath)
```

## QA Verification
1. Create a report setting with schedule=DAILY.
2. Run `python manage.py generate_scheduled_reports` → report must be generated.
3. Verify email is sent (check console backend in dev).
4. Run again immediately → report must NOT be re-generated (not due yet).
