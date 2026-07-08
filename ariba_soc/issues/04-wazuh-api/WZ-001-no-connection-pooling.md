# WZ-001: WazuhClient Creates New HTTP Connections Per Request

- **Severity**: Medium
- **Priority**: P2 (next sprint)
- **Category**: Wazuh API

## Current Problem
`wazuh_integration/services.py:12-36` uses `requests.get()` directly in `authenticate()` and `fetch_alerts()` without connection pooling:
```python
response = requests.get(
    f'{self.base_url}/security/user/authenticate',
    auth=(self.username, self.password),
    verify=self.verify_ssl,
    timeout=self.timeout,
    headers={'Content-Type': 'application/json'}
)
```
Each API call creates a new TCP connection, performs TLS handshake, and tears it down. For sync operations that may call multiple endpoints, this adds significant latency (3× RTT per request).

## Expected Behavior
Use `requests.Session()` for connection reuse across API calls within the same sync operation. TCP connections should be pooled and reused.

## Affected Files
- `wazuh_integration/services.py:12-86` (WazuhClient class)

## Suggested Fix
```python
class WazuhClient:
    def __init__(self):
        self.base_url = settings.WAZUH_API_URL or 'https://localhost:55000'
        self.username = settings.WAZUH_API_USERNAME or ''
        self.password = settings.WAZUH_API_PASSWORD or ''
        self.verify_ssl = settings.WAZUH_VERIFY_SSL
        self.timeout = settings.WAZUH_API_TIMEOUT
        self.token = None
        self.session = requests.Session()
        self.session.verify = self.verify_ssl
        # Configure adapter for connection pooling
        adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20)
        self.session.mount('https://', adapter)
```

## QA Verification
1. Run a Wazuh sync that fetches alerts and agents — measure total time before and after.
2. Enable `logging.getLogger('urllib3').setLevel(logging.DEBUG)` and verify that connections are reused (no "Starting new HTTPS connection" for every request).
