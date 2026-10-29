# 👥 User Guide: 03. Kanban Board Workflow

## 1. Board Layout & Column Modes
The **Alert Board** (`/board/`) visualizes alert workflows across lifecycle columns.

### View Mode Switcher:
- **Active Triage (6 Columns):** Displays alerts requiring immediate action (`New`, `Awaiting Action`, `In Progress`, `Pending`, `Escalated`, `Remediation`).
- **Resolved & Closed (4 Columns):** Displays completed investigations (`True Positives`, `False Positives`, `Closed Other`, `Archive`).
- **All Columns (10 Columns):** Comprehensive end-to-end view.

---

## 2. Drag-and-Drop Operations
You can transition alert states by dragging cards between columns:
- Dragging to **In Progress**: Automatically acknowledges the alert, stamps `acknowledged_at`, and stops the acknowledgment SLA clock.
- Dragging to **True Positives**: Sets status to `Closed` and automatically marks the verdict as `True Positive`.
- Dragging to **False Positives**: Sets status to `Closed` and automatically marks the verdict as `False Positive`.
- Dragging to **Archive**: Sets status to `Archived` for long-term historical retention.

---

## 3. Quick Board Filters
- **Filter by Severity:** One-click filter for `Critical`, `High`, `Medium`, or `Low` alerts.
- **My Alerts:** Instantly shows only cards assigned to the logged-in analyst.
- **Date Filters (Month & Year):** Filter alerts by calendar month or select `All Months` to view active alerts regardless of age.
