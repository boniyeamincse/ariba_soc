# SEC-013: No API token authentication

**Severity:** Medium  
**Priority:** P2  
**Category:** Missing Feature  
**Status:** Open  
**File:** `ariba_soc/alerts/views.py`

## Current Problem
JSON API endpoints use session authentication only. No support for programmatic access (SIEM integration, automation scripts).

## Expected Behavior
- API token authentication for programmatic access
- Token management UI
- Rate limiting per token

## Affected Files
- `ariba_soc/alerts/views.py` (all API views)
- `ariba_soc/config/settings.py`

## Suggested Fix
```bash
pip install djangorestframework
```
```python
# settings.py
INSTALLED_APPS += ['rest_framework', 'rest_framework.authtoken']

# views.py
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def alerts_api(request):
    # ...
```

## QA Verification
- Generate API token in settings
- Use token in `Authorization: Token <key>` header
- Access API without session cookie
