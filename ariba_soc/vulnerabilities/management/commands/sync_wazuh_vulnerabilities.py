import logging
from django.core.management.base import BaseCommand
from vulnerabilities.services.wazuh_reader import WazuhVulnerabilityReader
from vulnerabilities.services.normalizer import sync_vulnerability_from_indexer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync active vulnerabilities from Wazuh Indexer (wazuh-states-vulnerabilities-*)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--size',
            type=int,
            default=2000,
            help='Maximum number of vulnerability records to fetch (default: 2000)',
        )

    def handle(self, *args, **options):
        size = options['size']
        self.stdout.write(self.style.NOTICE(f'Connecting to Wazuh indexer to sync up to {size} vulnerabilities...'))

        reader = WazuhVulnerabilityReader()
        result = reader.fetch_vulnerabilities(size=size)

        if not result.get('success'):
            self.stderr.write(self.style.ERROR(f"Failed to fetch vulnerabilities: {result.get('message', 'Unknown error')}"))
            return

        vulns = result.get('vulnerabilities', [])
        total_found = result.get('total', 0)
        self.stdout.write(f'Found {total_found} vulnerabilities in Wazuh index. Retrieved {len(vulns)}.')

        created = 0
        updated = 0

        for vuln in vulns:
            _, was_created = sync_vulnerability_from_indexer(vuln)
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Sync complete! Successfully synced {len(vulns)} vulnerabilities ({created} newly created, {updated} updated).'
        ))
