from django.core.management.base import BaseCommand
from wazuh_integration.services import fetch_wazuh_alerts

class Command(BaseCommand):
    help = 'Sync alerts from Wazuh API'

    def add_arguments(self, parser):
        parser.add_argument('--time-range', default='1h', help='Time range for fetching alerts (e.g., 1h, 24h)')

    def handle(self, *args, **options):
        time_range = options['time_range']
        self.stdout.write(f'Syncing alerts from Wazuh (time range: {time_range})...')
        result = fetch_wazuh_alerts(time_range=time_range)
        self.stdout.write(self.style.SUCCESS(f'Sync complete: {result["fetched"]} fetched, {result["created"]} new alerts'))
