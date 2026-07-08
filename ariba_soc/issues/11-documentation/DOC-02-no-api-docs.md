# DOC-02: No API Documentation

- **Severity**: Medium
- **Priority**: P2 (next sprint)
- **Category**: Documentation

## Current Problem
The project provides two JSON API endpoints:
- `GET /api/alerts/` — returns all alerts
- `POST /api/alerts/<id>/move/` — drag-and-drop alert status change

Neither endpoint has any documentation. There is no:
- OpenAPI/Swagger spec
- API route listing
- Request/response schema documentation
- Authentication requirements documented

Consumers of the API (the frontend JS, future mobile app, or third-party integrations) have no specification to code against.

## Expected Behavior
API endpoints should be documented using `drf-spectacular` (or similar) with a browsable Swagger UI at `/api/docs/`. At minimum, a markdown file should document the endpoints, request bodies, and response formats.

## Affected Files
- `config/urls.py` (needs Swagger UI routes)
- `alerts/views.py:254-291` (API endpoints)
- `docs/api.md` (needs to be created)

## Suggested Fix
Option A (lightweight): Create `docs/api.md` documenting the endpoints manually.
Option B (recommended): Install `drf-spectacular` and generate OpenAPI schema:

```python
# urls.py
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns += [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger'),
]
```

```python
# alerts/views.py (add docstrings)
def alerts_api(request):
    """
    GET /api/alerts/
    Returns the 100 most recent alerts with key fields.
    Response: { "alerts": [{ "id", "alert_name", "severity", ... }] }
    """
```

## QA Verification
1. Navigate to `/api/docs/` — Swagger UI must load and display all endpoints.
2. Each endpoint must show request/response schema.
3. The schemas must accurately reflect the actual data returned.
