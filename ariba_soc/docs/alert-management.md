# Alert Management

## Alert Lifecycle

```
                  ┌──────────────┐
                  │     New      │
                  └──────┬───────┘
                         │
                    Acknowledge
                         │
                         ▼
               ┌─────────────────┐
          ┌────│  Acknowledged    │────┐
          │    └────────┬─────────┘    │
          │             │              │
          │        Investigate         │
          │             │              │
          │             ▼              │
          │    ┌─────────────────┐     │
          │    │   In Progress    │     │
          │    └────────┬─────────┘     │
          │             │              │
       ┌──┴──┐        ┌──┴──┐        ┌──┴──┐
       │Esc.│        │Res.│        │Cl. │
       └──┬──┘        └──┬──┘        └──┬──┘
          │              │              │
          ▼              ▼              ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │Escalated │   │ Resolved │   │  Closed   │
   └──────────┘   └──────────┘   └──────────┘
```

### Statuses

| Status | Description | Set By |
|--------|-------------|--------|
| `new` | Ingested from Wazuh, not yet reviewed | System |
| `acknowledged` | L1 has reviewed and taken ownership | L1/L2 |
| `in_progress` | Active investigation underway | L2 |
| `resolved` | Issue addressed, monitoring | L2 |
| `closed` | No further action needed | L2/Manager/Admin |
| `escalated` | Requires higher-tier analysis | L1 → L2 |

## Alert Deduplication

When syncing from Wazuh, each alert is checked against `wazuh_alert_id` (unique field on `Alert`).

- If `wazuh_alert_id` already exists → skip (logged as `alerts_skipped`)
- If new → create `Alert` record (logged as `alerts_created`)

This prevents duplicate alerts across multiple sync operations.

## Alert Source Tracking

Two mechanisms:
1. **`AlertSource` model** — optional link to a named source configuration
2. **`Alert.source` CharField** — direct source name string (used when no AlertSource link)

## Severity Levels

| Level | Color | SLA Target | Description |
|-------|-------|------------|-------------|
| Critical | Red | 4 hours | Immediate threat, active compromise |
| High | Orange | 8 hours | Potential threat, urgent investigation |
| Medium | Yellow | 24 hours | Suspicious activity, further analysis |
| Low | Blue | 72 hours | Informational, routine review |
| Info | Gray | N/A | Log data, no action required |

## SLA Enforcement

Settings managed via `settings_manager`:
- `SLA_HOURS`: Default SLA target (24 hours)
- `AUTO_ESCALATE_AFTER_HOURS`: Auto-escalate if alert remains unresolved (48 hours)
- `MAX_ESCALATIONS_PER_ALERT`: Max escalation depth (3)

## Notifications

On assignment or escalation:
1. An in-app `Notification` record is created for the assignee
2. If email is configured, an email notification is sent
3. Notification bell icon in navbar shows unread count

## Audit Trail

Every status change and assignment is recorded in `AlertAuditLog`:
- `action`: `status_change`, `assignment`, `escalation`, `comment`
- `old_value` / `new_value`: Previous → current values
- `actor`: Who performed the action
- `timestamp`: When it happened
