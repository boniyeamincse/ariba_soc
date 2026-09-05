# DB-003: No Bulk Create Operations for Alert Imports

- **Severity**: Medium
- **Priority**: P2 (next sprint)
- **Category**: Database

## Current Problem
`wazuh_integration/services.py:166-178` creates alerts one at a time inside a loop:
```python
for wazuh_alert in alerts_data:
    alert_id = str(wazuh_alert.get('id', ''))
    if not alert_id:
        continue
    if Alert.objects.filter(wazuh_alert_id=alert_id).exists():
        continue
    try:
        data = normalize_alert(wazuh_alert)
        data['source'] = source
        Alert.objects.create(**data)
        created_count += 1
    except Exception as e:
        logger.error(f'Failed to save alert {alert_id}: {e}')
```
For the default batch of 500 alerts, this generates 500 individual `INSERT` statements plus N existence-check queries. With a high volume of alerts, this is extremely slow and transaction-heavy.

## Expected Behavior
Use Django's `bulk_create` with `ignore_conflicts=True` to batch insert all new alerts in a single query. Use a pre-fetched set of existing `wazuh_alert_id` values to avoid N+1 existence checks.

## Affected Files
- `wazuh_integration/services.py:154-199`

## Suggested Fix
```python
existing_ids = set(Alert.objects.filter(
    wazuh_alert_id__in=[str(a.get('id', '')) for a in alerts_data if a.get('id')]
).values_list('wazuh_alert_id', flat=True))

batch = []
for wazuh_alert in alerts_data:
    alert_id = str(wazuh_alert.get('id', ''))
    if not alert_id or alert_id in existing_ids:
        continue
    try:
        data = normalize_alert(wazuh_alert)
        data['source'] = source
        batch.append(Alert(**data))
    except Exception as e:
        logger.error(f'Failed to normalize alert {alert_id}: {e}')

if batch:
    Alert.objects.bulk_create(batch, ignore_conflicts=True, batch_size=100)
```

## QA Verification
1. Run a Wazuh sync with 500 alerts — measure time before and after fix (expect >5x improvement).
2. Verify no duplicate alerts are created (unique constraint on wazuh_alert_id).
3. Verify `created_count` matches the actual number of new alerts.
