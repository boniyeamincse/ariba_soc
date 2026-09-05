# SEC-011: HTTP used for external API calls

**Severity:** Medium  
**Priority:** P2  
**Category:** Security (MITM)  
**Status:** Open  
**File:** `ariba_soc/monitor/services.py`

## Current Problem
`monitor/services.py` uses `http://ip-api.com/json/{ip}` (HTTP) for geolocation, which can be intercepted (MITM) to return false data.

## Expected Behavior
All external API calls use HTTPS.

## Affected Files
- `ariba_soc/monitor/services.py` (line 227)

## Suggested Fix
```python
# Before
response = requests.get(f"http://ip-api.com/json/{ip}")

# After
response = requests.get(f"https://ip-api.com/json/{ip}", timeout=5)
```

## QA Verification
- Check all external HTTP calls use HTTPS
- Network trace shows TLS encrypted traffic
