# WZ-003: Wazuh API Token Never Refreshed After Expiry

- **Severity**: Medium
- **Priority**: P2 (next sprint)
- **Category**: Wazuh API

## Current Problem
`wazuh_integration/services.py:38-44` authenticates once and stores the token:
```python
def get_headers(self):
    if not self.token:
        self.authenticate()
    return {
        'Authorization': f'Bearer {self.token}',
        'Content-Type': 'application/json',
    }
```
If the token expires (Wazuh default: 15 minutes), subsequent API calls will fail with 401. The sync operation that fetches both alerts and agents may take more than 15 minutes for large volumes, and `wazuh_agents` (a separate view) also shares the client instance but re-authenticates only if `self.token` is `None`.

## Expected Behavior
On receiving a 401 response, the client should automatically re-authenticate and retry the request once.

## Affected Files
- `wazuh_integration/services.py:38-44` (get_headers)
- `wazuh_integration/services.py:21-36` (authenticate)

## Suggested Fix
Add automatic token refresh on 401:
```python
def _request(self, method, url, **kwargs):
    for attempt in range(2):
        if not self.token:
            self.authenticate()
        kwargs['headers'] = kwargs.get('headers', {})
        kwargs['headers'].update(self.get_headers())
        response = self.session.request(method, url, **kwargs)
        if response.status_code == 401 and attempt == 0:
            self.token = None  # Force re-auth
            continue
        response.raise_for_status()
        return response
    return response
```

## QA Verification
1. After authenticating, manually invalidate the Wazuh API token on the Wazuh server.
2. Make a second API call — it must automatically re-authenticate and succeed.
3. Verify the sync log shows `Success` status even when a mid-sync token expiry occurs.
