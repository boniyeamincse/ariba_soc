# WZ-002: Wazuh Alert Sync Fetches Only 500 Alerts, No Pagination

- **Severity**: High
- **Priority**: P1 (this sprint)
- **Category**: Wazuh API

## Current Problem
`wazuh_integration/services.py:46-71` hardcodes `limit=500` and never iterates over pages:
```python
def fetch_alerts(self, limit=500, offset=0, time_range='1h'):
    params = {
        'limit': limit,
        'offset': offset,
        'sort': '-timestamp',
    }
```
The calling function `fetch_wazuh_alerts()` at line 162 calls this once with default offset:
```python
result = client.fetch_alerts(time_range=time_range)
alerts_data = result.get('data', {}).get('items', []) ...
```
If there are more than 500 alerts in the time range, the rest are silently ignored. This means a 1-hour sync can miss alerts if the SOC generates more than 500 alerts per hour.

## Expected Behavior
The sync should loop over pages (using offset/limit) until all alerts in the time range are fetched, or until a configurable maximum is reached. Each page should be processed and the total counters should reflect all fetched alerts.

## Affected Files
- `wazuh_integration/services.py:46-71` (fetch_alerts)
- `wazuh_integration/services.py:154-199` (fetch_wazuh_alerts)

## Suggested Fix
```python
def fetch_alerts(self, time_range='1h', max_alerts=5000):
    all_items = []
    offset = 0
    limit = 500
    
    while offset < max_alerts:
        params = {'limit': limit, 'offset': offset, 'sort': '-timestamp'}
        since = ...
        params['q'] = f'timestamp>{since}'
        
        response = self.session.get(
            f'{self.base_url}/alerts',
            headers=self.get_headers(),
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        items = data.get('data', {}).get('items', []) or data.get('data', {}).get('affected_items', [])
        if not items:
            break
        all_items.extend(items)
        offset += limit
        
    return {'data': {'items': all_items}}
```

## QA Verification
1. In a test environment, have >500 alerts in the last hour.
2. Run a sync — verify `alerts_fetched` count reflects all alerts, not just 500.
3. Verify the `WazuhSyncLog` records the correct total.
