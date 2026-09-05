from django.core.management.base import BaseCommand
from django.utils import timezone
from alerts.models import AlertAuditLog, AlertComment
from audit.models import AuditLog
from settings_manager.models import SettingAuditLog, AuditLogSetting


class Command(BaseCommand):
    help = 'Clean up orphaned audit logs and comments older than retention period'

    def handle(self, *args, **options):
        retention = AuditLogSetting.objects.filter(log_enabled=True).values_list('retention_days', flat=True).first()
        if not retention:
            retention = 365

        cutoff = timezone.now() - timezone.timedelta(days=retention)
        deleted = 0

        for model, name in [
            (AlertAuditLog, 'Alert audit logs'),
            (AlertComment, 'Alert comments'),
            (AuditLog, 'Audit logs'),
            (SettingAuditLog, 'Setting audit logs'),
        ]:
            qs = model.objects.filter(created_at__lt=cutoff)
            count = qs.count()
            if count:
                qs.delete()
                deleted += count
                self.stdout.write(f'Deleted {count} old {name}')

        self.stdout.write(self.style.SUCCESS(f'Cleanup complete. Deleted {deleted} records.'))
