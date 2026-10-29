import logging
from django.core.management.base import BaseCommand
from alerts.models import Alert
from wazuh_integration.services import extract_wazuh_network_process_fields

logger = logging.getLogger('ariba_soc.wazuh_integration')


class Command(BaseCommand):
    help = 'Reparse network, process, user and enrichment fields for alerts from their raw_json / alert_fields.'

    def add_arguments(self, parser):
        parser.add_argument('--alert-id', type=str, default=None, help='Filter by specific Alert DB ID or Wazuh Alert ID')
        parser.add_argument('--limit', type=int, default=None, help='Maximum number of alerts to process')
        parser.add_argument('--dry-run', action='store_true', help='Preview changes without saving to database')
        parser.add_argument('--force', action='store_true', help='Overwrite existing values with newly extracted values')

    def handle(self, *args, **options):
        alert_id = options.get('alert_id')
        limit = options.get('limit')
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)

        qs = Alert.objects.all().order_by('-id')
        if alert_id:
            if str(alert_id).isdigit():
                qs = qs.filter(id=int(alert_id))
            else:
                qs = qs.filter(wazuh_alert_id=alert_id)

        if limit:
            qs = qs[:limit]

        total = qs.count() if not limit else len(qs)
        self.stdout.write(f'Scanning {total} alerts for re-parsing (dry-run: {dry_run}, force: {force})...')

        field_names = [
            'source_ip', 'destination_ip', 'username',
            'process_name', 'process_user', 'command_line',
            'target_file', 'file_path', 'file_hash_md5',
            'file_hash_sha1', 'file_hash_sha256', 'url'
        ]

        updated_count = 0
        for alert in qs:
            doc = alert.raw_json or alert.alert_fields or {}
            if not doc:
                continue

            extracted = extract_wazuh_network_process_fields(doc)
            updated_fields = []

            for field in field_names:
                ext_val = extracted.get(field)
                if not ext_val:
                    continue
                current_val = getattr(alert, field, None)
                if force or not current_val:
                    if current_val != ext_val:
                        setattr(alert, field, ext_val)
                        updated_fields.append(f"{field}='{ext_val}'")

            if updated_fields:
                updated_count += 1
                if not dry_run:
                    alert.save(update_fields=[f.split('=')[0] for f in updated_fields])
                self.stdout.write(
                    f"Alert #{alert.id} ({alert.wazuh_alert_id}): updated {', '.join(updated_fields)}"
                )

        self.stdout.write(
            self.style.SUCCESS(f'Done. Successfully re-parsed {updated_count}/{total} alerts.')
        )
