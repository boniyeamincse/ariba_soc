# Alerts Module

## Purpose

Core module for managing security alerts — CRUD, triage, collaboration, and notifications.

## Key Models

### `Alert`
- **wazuh_alert_id** (unique, nullable): Wazuh alert ID for dedup
- **severity:** critical/high/medium/low/info
- **status:** new/acknowledged/in_progress/resolved/closed/escalated
- **rule_id, rule_description:** Wazuh rule info
- **agent_id, agent_name:** Monitored host info
- **source, source_ip:** Alert origin
- **assigned_to, escalated_to:** FK to User
- **acknowledged_at, resolved_at:** Timestamps
- **raw_data:** JSONField storing original Wazuh payload
- **created_at, updated_at:** Auto timestamps

### `AlertComment`
- FK to Alert + User author
- Free-text content

### `AlertAuditLog`
- Tracks status_change, assignment, escalation, comment actions
- Stores old_value/new_value for change tracking

### `Notification`
- Per-user notification on assignment/escalation/status change
- is_read boolean for read/unread tracking

## Key Views

| View | Type | Description |
|------|------|-------------|
| `alert_table` | GET | Sortable, filterable table with pagination |
| `alert_board` | GET | Kanban board with drag-and-drop columns |
| `my_alerts` | GET | Table filtered to current user |
| `alert_detail` | GET | Full alert view with comments + audit trail |
| `edit_alert_ajax` | POST | JSON endpoint for status changes |
| `assign_ajax` | POST | JSON endpoint for assignment |
| `escalate_ajax` | POST | JSON endpoint for escalation |
| `add_comment` | POST | Add comment to alert |

## Business Logic

- **Status transitions:** L1 can move new → acknowledged → escalated; L2 can move any → in_progress/resolved/closed
- **Assignment:** Creates AlertAuditLog + Notification + optional email
- **Escalation:** Creates escalation chain, increments escalation count
- **Dedup:** wazuh_alert_id unique constraint prevents duplicate ingestion

## URLs

```
/alerts/table/
/alerts/board/
/alerts/my-alerts/
/alerts/<id>/
/alerts/<id>/edit/
/alerts/<id>/assign/
/alerts/<id>/escalate/
/alerts/<id>/comment/
```

## Dependencies

- **accounts:** Role checks via AnalystProfile
- Used by: dashboard, reports
