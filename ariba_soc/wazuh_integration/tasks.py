from .services import fetch_wazuh_alerts

def run_scheduled_sync():
    try:
        result = fetch_wazuh_alerts(time_range='24h')
        print(f'Scheduled sync: {result}')
    except Exception as e:
        print(f'Scheduled sync failed: {e}')
