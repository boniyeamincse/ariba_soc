# UI & User Guide

## Navigation

The application has a top navigation bar (`base.html`) with role-aware items:

| Nav Item | L1 | L2 | Manager | Admin |
|----------|----|----|---------|-------|
| Dashboard | ✅ | ✅ | ✅ | ✅ |
| Alert Table | ✅ | ✅ | ✅ | ✅ |
| Alert Board | ✅ | ✅ | ✅ | ✅ |
| My Alerts | ✅ | ✅ | ✅ | ✅ |
| Reports | ❌ | ❌ | ✅ | ✅ |
| Settings | ❌ | ❌ | ❌ | ✅ |
| Audit Log | ❌ | ❌ | ❌ | ✅ |
| Wazuh Integration | ❌ | ❌ | ❌ | ✅ |
| Profile | ✅ | ✅ | ✅ | ✅ |

## Dashboard (`/`)

The main dashboard displays:
- **Stat cards:** Total alerts, critical alerts, by status counts
- **Severity breakdown chart:** Bar chart (critical/high/medium/low/info)
- **Daily trend chart:** Line chart of alerts over last 14 days
- **Status distribution:** Pie chart
- **Recent alerts:** Last 10 alerts with quick links
- **Top analysts:** By resolved/closed count

## Alert Table (`/alerts/table/`)

A sortable, filterable table with all alerts:
- **Filters:** Severity, status, date range, agent ID, rule ID, free-text search
- **Columns:** ID, severity badge, title, status badge, source, agent, assigned to, created date
- **Actions:** Click row to view detail; inline status change via AJAX
- **Pagination:** 25 alerts per page

## Alert Board (`/alerts/board/`)

Kanban-style drag-and-drop board:
- **Columns:** New, Acknowledged, In Progress, Resolved, Closed, Escalated
- **Cards:** Each alert as a draggable card showing severity badge, title, agent, time
- **Drag-and-drop:** Move cards between columns to change status (AJAX)
- **Role limits:** L1 can only see New + Acknowledged columns; L2 sees all

## My Alerts (`/alerts/my-alerts/`)

Filtered table showing only alerts assigned to the current user.

## Alert Detail (`/alerts/<id>/`)

Full alert view with:
- Alert metadata (severity, status, agent, source, timestamps)
- Raw Wazuh JSON data in collapsible section
- Comments thread (add comment form)
- Audit log of status changes
- Assign action (Manager/L2/Admin)
- Escalate action (L1/L2)
- Status change buttons

## Settings (`/settings/`)

Admin-only panel:
- List all system settings by category
- Edit values inline
- Audit trail of setting changes

## Audit Log (`/audit/`)

Admin-only view:
- Filterable table of all system actions
- Columns: timestamp, actor, action, model, object ID, IP address

## Wazuh Integration (`/wazuh/status/`)

Admin-only integration management:
- **Manager Config tab:** Add/edit Manager API credentials, test connection
- **Indexer Config tab:** Add/edit Indexer credentials, test connection
- **Sync History tab:** Log of sync operations
- **Force Sync button:** Trigger immediate alert import

## Reports (`/reports/`)

Manager/Admin only:
- **Alert Report:** Filter by date range, severity, analyst
- **Analyst Performance Report:** Metrics by analyst
- **Export:** PDF or CSV format

## Theme

Dark glassmorphism design:
- Semi-transparent glass panels with `backdrop-filter: blur()`
- Dark background with gradient
- Bootstrap 5 components with custom CSS overrides
- Responsive for desktop and tablet
- Severity color coding: critical (red), high (orange), medium (yellow), low (blue), info (gray)
- Status badges with distinct colors per status
