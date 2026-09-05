# Reports Module

## Purpose

Generates PDF and CSV exports for security alerts and analyst performance metrics.

## Key Views

### `generate_report` (GET `/reports/alerts/`)
Alert report with query parameters:
- `format`: `pdf` or `csv`
- `from` / `to`: Date range (YYYY-MM-DD)
- `severity`: Filter (optional)
- `assigned_to`: User ID filter (optional)

Output:
- **PDF:** WeasyPrint-rendered HTML table → PDF file
- **CSV:** Streaming CSV with header row + data rows

### `analyst_performance_report` (GET `/reports/analyst-performance/`)
Performance metrics per analyst:
- `format`: `pdf` or `csv`
- `from` / `to`: Date range

Metrics: total assigned, total resolved, total closed, avg resolution time.

## Key Utils (`utils.py`)

### PDF Generation
```python
def render_to_pdf(template_path, context):
    """Render Django template to PDF using WeasyPrint."""
    html = render_to_string(template_path, context)
    pdf = HTML(string=html).write_pdf()
    return pdf
```

### CSV Generation
```python
def render_to_csv(columns, rows):
    """Generate streaming CSV response."""
    response = HttpResponse(content_type='text/csv')
    writer = csv.writer(response)
    writer.writerow(columns)
    for row in rows:
        writer.writerow(row)
    return response
```

## Access Control

- Manager and Admin roles only
- L1 and L2 analysts cannot access report views

## Dependencies

- **alerts:** Alert data for reports
- **accounts:** Analyst performance data
- External: WeasyPrint (PDF rendering)
