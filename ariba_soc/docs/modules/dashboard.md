# Dashboard Module

## Purpose

Provides the main landing page with KPIs, charts, and recent activity overview.

## Key Views

### `dashboard_home` (GET `/`)
Main dashboard page rendering:
- **Stat cards:** Total alerts, critical alerts, new/acknowledged/resolved counts (aggregated via SQL)
- **Severity breakdown chart:** Bar chart data via `/api/severity-breakdown/`
- **Daily trend chart:** Line chart (last 14 days) via `/api/daily-trend/`
- **Status distribution:** Pie chart via `/api/status-distribution/`
- **Recent alerts:** Last 10 alerts with quick links
- **Top analysts:** Resolved/closed counts per analyst

### Chart Data APIs

All return JSON with `labels` and `data` arrays.

**`severity_breakdown`:**
```json
{"labels": ["critical", "high", "medium", "low", "info"], "data": [5, 15, 30, 10, 2]}
```

**`daily_trend`:**
```json
{"labels": ["2026-07-01", "2026-07-02", ...], "data": [8, 12, ...]}
```

**`status_distribution`:**
```json
{"labels": ["new", "acknowledged", "in_progress", "resolved", "closed", "escalated"], "data": [20, 15, 10, 25, 20, 5]}
```

## Template

`templates/ariba_soc/dashboard.html` — Extends `base.html`, renders chart containers, stat cards, and recent alerts table.

## Dependencies

- **alerts:** Queries Alert model for aggregates
- **accounts:** Analyst role for performance stats
