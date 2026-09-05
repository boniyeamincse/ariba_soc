Add this section to your `AI.md` / coding AI instruction.

````md
## Settings Menu and Sub Menu

Create a main sidebar menu called:

Settings

Only Admin, SOC Manager, and SOC Engineer can access the Settings menu.

SOC L1 and SOC L2 should not see system-level settings unless permission is given.

---

## Settings Sub Menus

The Settings menu must contain these sub menus:

1. User Management
2. Role & Permission
3. Analyst Profile
4. Wazuh API Settings
5. Alert Source Settings
6. Severity Settings
7. Status Settings
8. Verdict Settings
9. SLA Settings
10. Escalation Settings
11. Notification Settings
12. Report Settings
13. Dashboard Settings
14. Audit Log Settings
15. System Settings

---

## 1. User Management

Purpose:

Manage dashboard users.

Features:

- Create user
- Edit user
- Disable user
- Reset password
- Assign role
- Assign team
- View user activity
- View last login
- Activate/deactivate user

Fields:

- Full Name
- Username
- Email
- Phone
- Designation
- Department
- Role
- Team
- Status
- Last Login

Allowed roles:

- SOC L1
- SOC L2
- SOC Engineer
- SOC Manager
- Admin

---

## 2. Role & Permission

Purpose:

Control what each role can do.

Features:

- Create role
- Edit role
- Assign permissions
- View permission matrix

Permission examples:

- View alerts
- Assign alerts
- Edit alerts
- Close alerts
- Escalate alerts
- Change severity
- Change verdict
- View reports
- Export reports
- Manage settings
- View audit logs
- Sync Wazuh alerts

Role permission rule:

SOC L1:
- View own alerts
- Assign alert to self
- Add comment
- Update status
- Escalate alert
- Close false positive alert

SOC L2:
- All L1 permissions
- View escalated alerts
- Reassign alerts
- Close true positive alert
- Add remediation note

SOC Engineer:
- View all alerts
- Manage Wazuh settings
- Manage alert source
- Manage rule mapping
- View false positive trends

SOC Manager:
- View all dashboards
- Assign alerts
- View reports
- Export reports
- View analyst performance
- View SLA status

Admin:
- Full access

---

## 3. Analyst Profile

Purpose:

Manage analyst information.

Features:

- Analyst profile list
- Analyst role assignment
- Analyst shift/team assignment
- Analyst active/inactive status
- Workload visibility

Fields:

- User
- SOC Role
- Team
- Shift
- Phone
- Designation
- Is Active
- Supervisor

---

## 4. Wazuh API Settings

Purpose:

Manage Wazuh API connection.

Fields:

- Wazuh API URL
- Wazuh API Username
- Wazuh API Password
- SSL Verify True/False
- API Timeout
- Sync Interval
- Last Sync Time
- Connection Status

Features:

- Test connection button
- Save settings
- Manual sync button
- Show last sync result
- Show API error safely

Security rule:

Never show the Wazuh API password after saving.
Never expose Wazuh token in frontend.
Store secrets in environment variables or encrypted database field.

---

## 5. Alert Source Settings

Purpose:

Manage alert sources.

Default source:

- Wazuh

Optional future sources:

- Email
- IDS
- EDR
- Firewall
- SIEM

Fields:

- Source Name
- Source Type
- Description
- Is Active

Features:

- Add source
- Edit source
- Disable source
- Map source to alert type

---

## 6. Severity Settings

Purpose:

Manage alert severity levels.

Default values:

- Informational
- Low
- Medium
- High
- Critical

Fields:

- Severity Name
- Severity Score
- Color
- SLA Acknowledge Time
- SLA Resolve Time
- Is Active

Color mapping:

- Informational = Gray
- Low = Green
- Medium = Yellow
- High = Orange
- Critical = Red

Rules:

- Critical alerts must be shown at top priority.
- High and Critical alerts should be visible in manager dashboard.
- Severity change must require analyst comment.

---

## 7. Status Settings

Purpose:

Manage alert workflow status.

Default statuses:

- New
- Awaiting Action
- In Progress
- Pending
- Escalated
- Closed
- Archived

Fields:

- Status Name
- Status Type
- Color
- Sort Order
- Is Final Status
- Is Active

Workflow rule:

New → In Progress → Pending/Escalated → Closed → Archived

Validation:

- Closed alert must have verdict.
- Archived alert must already be closed.
- Escalated alert must have escalation reason.

---

## 8. Verdict Settings

Purpose:

Manage alert classification.

Default verdicts:

- None
- True Positive
- False Positive
- Benign Positive
- Suspicious
- Duplicate
- Test Activity

Fields:

- Verdict Name
- Verdict Type
- Color
- Requires Comment
- Is Active

Validation:

- True Positive requires analyst comment.
- False Positive requires reason.
- Closed alert cannot have verdict None.

---

## 9. SLA Settings

Purpose:

Manage alert response SLA.

Default SLA:

Critical:
- Acknowledge within 15 minutes
- Resolve/update within 1 hour

High:
- Acknowledge within 30 minutes
- Resolve/update within 4 hours

Medium:
- Acknowledge within 2 hours
- Resolve/update within 1 business day

Low:
- Acknowledge within 1 business day
- Resolve within 3 business days

Fields:

- Severity
- Acknowledge Time
- Resolve Time
- Breach Warning Time
- Is Active

Features:

- SLA breach indicator
- SLA warning indicator
- SLA report
- Manager dashboard SLA widget

---

## 10. Escalation Settings

Purpose:

Define when and how alerts are escalated.

Escalation conditions:

- Critical severity
- Mimikatz detected
- Malware detected
- Credential dumping detected
- Lateral movement suspected
- Data exfiltration suspected
- Suspicious PowerShell
- Business-critical host affected
- L1 cannot classify
- Repeated brute-force attack

Fields:

- Rule Name
- Severity Condition
- Alert Name Keyword
- Wazuh Rule ID
- Escalate To Role
- Escalate To User
- Is Active

Features:

- Auto-escalation rule
- Manual escalation
- Escalation reason required
- Escalation history

---

## 11. Notification Settings

Purpose:

Notify analysts and managers about important alerts.

Notification channels:

- Email
- Dashboard notification
- SMS optional
- Microsoft Teams optional

Notification events:

- New critical alert
- Alert assigned
- Alert escalated
- SLA breach
- Alert closed
- True positive confirmed

Fields:

- Notification Name
- Event Type
- Channel
- Recipient Role
- Recipient User
- Is Active

Rules:

- Critical alert should notify SOC Manager and L2.
- SLA breach should notify SOC Manager.
- Escalated alert should notify assigned L2 analyst.

---

## 12. Report Settings

Purpose:

Manage report format and schedule.

Reports:

- Daily SOC Report
- Weekly SOC Report
- Monthly SOC Report
- Analyst Performance Report
- SLA Breach Report
- True Positive Report
- False Positive Report

Fields:

- Report Name
- Report Type
- Schedule
- Recipient Email
- Export Format
- Is Active

Export formats:

- PDF
- CSV
- Excel

Features:

- Manual export
- Scheduled report
- Report preview
- Report download

---

## 13. Dashboard Settings

Purpose:

Customize dashboard display.

Features:

- Configure visible widgets
- Configure default date range
- Configure default landing page
- Configure chart refresh interval
- Configure board columns

Fields:

- Default Page
- Default Date Range
- Auto Refresh Interval
- Show KPI Cards
- Show Charts
- Show Analyst Workload
- Show SLA Widget

Default landing page by role:

SOC L1:
- Assigned Alerts

SOC L2:
- Escalated Alerts

SOC Manager:
- Management Dashboard

SOC Engineer:
- Wazuh Sync / Alert Quality Dashboard

Admin:
- Main Dashboard

---

## 14. Audit Log Settings

Purpose:

Control audit logging behavior.

Audit must capture:

- Alert created
- Alert assigned
- Status changed
- Severity changed
- Verdict changed
- Comment added
- Alert escalated
- Alert closed
- Alert archived
- User login
- User logout
- Settings changed
- Wazuh sync executed

Fields:

- Action Type
- Log Enabled
- Retention Days
- Is Critical Action

Rules:

- Alert changes must always be audited.
- Settings changes must always be audited.
- Audit logs should not be editable by normal users.
- Only Admin and SOC Manager can view audit logs.

---

## 15. System Settings

Purpose:

General application settings.

Fields:

- Application Name
- Company Name
- Timezone
- Date Format
- Session Timeout
- Pagination Size
- Maintenance Mode
- System Email
- Logo Upload

Default values:

- Application Name: Ariba SOC Alert Dashboard
- Company Name: Akij Group
- Timezone: Asia/Dhaka
- Date Format: DD MMM YYYY HH:mm
- Pagination Size: 25

---

## Sidebar Menu Structure

Use this sidebar structure:

```txt
Dashboard
Alert Board
Alert Table
Assigned Alerts
Escalated Alerts
Reports
Wazuh Sync
Audit Logs
Settings
    ├── User Management
    ├── Role & Permission
    ├── Analyst Profile
    ├── Wazuh API Settings
    ├── Alert Source Settings
    ├── Severity Settings
    ├── Status Settings
    ├── Verdict Settings
    ├── SLA Settings
    ├── Escalation Settings
    ├── Notification Settings
    ├── Report Settings
    ├── Dashboard Settings
    ├── Audit Log Settings
    └── System Settings
````

---

## Django URL Structure

Create URLs like this:

```txt
/settings/users/
/settings/roles/
/settings/analysts/
/settings/wazuh-api/
/settings/alert-sources/
/settings/severities/
/settings/statuses/
/settings/verdicts/
/settings/sla/
/settings/escalation/
/settings/notifications/
/settings/reports/
/settings/dashboard/
/settings/audit-log/
/settings/system/
```

---

## Django Apps for Settings

Create a separate Django app:

```txt
settings_manager/
```

Suggested structure:

```txt
settings_manager/
├── models.py
├── views.py
├── forms.py
├── urls.py
├── admin.py
├── services.py
└── templates/settings_manager/
    ├── base_settings.html
    ├── user_management.html
    ├── role_permission.html
    ├── analyst_profile.html
    ├── wazuh_api_settings.html
    ├── alert_source_settings.html
    ├── severity_settings.html
    ├── status_settings.html
    ├── verdict_settings.html
    ├── sla_settings.html
    ├── escalation_settings.html
    ├── notification_settings.html
    ├── report_settings.html
    ├── dashboard_settings.html
    ├── audit_log_settings.html
    └── system_settings.html
```

---

## Settings UI Requirement

Each settings page must have:

* Page title
* Short description
* Add button
* Data table
* Edit button
* Active/inactive toggle
* Save button
* Cancel button
* Search option
* Pagination
* Audit log entry after change

Use dark SOC theme consistent with the dashboard.

---

## Permission Rule for Settings

Settings access:

Admin:

* Full access

SOC Manager:

* View and manage reports, dashboard, SLA, escalation, user assignment

SOC Engineer:

* Manage Wazuh API, alert sources, severity, status, verdict, rule mapping

SOC L2:

* View limited SLA and escalation settings only if allowed

SOC L1:

* No settings access by default

---

## Important Validation Rules

* Wazuh API settings require connection test before activation.
* Severity name cannot be duplicate.
* Status name cannot be duplicate.
* Verdict name cannot be duplicate.
* SLA cannot be empty for active severity.
* Escalation rule must have target role or target user.
* System timezone must be valid.
* Role permission changes must be audited.
* Admin user cannot be disabled if it is the only active admin.

---

## Expected Output

AI developer must create:

* Settings sidebar menu
* Settings submenu
* Settings pages
* Django models
* Django forms
* Django views
* Django URLs
* Templates
* Role-based permission checks
* Audit logging for settings changes
* Dark SOC-style UI

```

Use this instruction after your main dashboard instruction so the coding AI understands the full **Settings menu and submenu** requirement.
```
