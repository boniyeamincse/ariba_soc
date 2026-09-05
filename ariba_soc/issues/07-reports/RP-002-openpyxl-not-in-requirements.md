# RP-002: openpyxl Dependency Not Declared

- **Severity**: Medium
- **Priority**: P1 (this sprint)
- **Category**: Reports

## Current Problem
`reports/views.py:48-67` imports `openpyxl` inside the function with a try/except:
```python
try:
    import openpyxl
    ...
except ImportError:
    return HttpResponse('openpyxl not installed. Install with: pip install openpyxl')
```
However, there is no `requirements.txt` file at all (see DEP-02). Even after generating one, `openpyxl` must be included. When the app is deployed without `openpyxl`, the Excel export function returns a plain text error message instead of a proper error page or fallback to CSV.

## Expected Behavior
- `openpyxl` must be listed in `requirements.txt`
- If unavailable at runtime, the UI should hide the Excel export button rather than show an error
- The download route should return a proper error response (JSON or styled page), not plain text

## Affected Files
- `reports/views.py:48-67` (export_excel)
- `templates/ariba_soc/reports_home.html` (should conditionally show Excel button)

## Suggested Fix
1. Check import at module level with a flag:
```python
try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False
```
2. In the template:
```html
{% if HAS_OPENPYXL %}
<a href="{% url 'reports:export_excel' %}" class="btn btn-ariba-outline">
    <i class="bi bi-file-earmark-excel"></i> Export Excel
</a>
{% endif %}
```

## QA Verification
1. Without `openpyxl` installed → Excel export button must be hidden.
2. With `openpyxl` installed → Excel export button must appear and work.
3. `requirements.txt` must contain `openpyxl`.
