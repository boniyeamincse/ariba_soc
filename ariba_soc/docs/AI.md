# AI.md — Ariba SOC Alert Management Dashboard

## 1. Project Vision

Build **Ariba SOC Alert Management Dashboard**, a Django-based SOC management dashboard for Wazuh alerts.

The dashboard must help SOC L1, L2, SOC Engineer, and SOC Manager manage alerts from detection to closure. The system is not only a technical alert viewer; it is a complete **alert triage, assignment, escalation, verdict, reporting, and management dashboard**.

The dashboard must be based on:

- Backend: Python Django
- Frontend: Django Template + HTML + CSS + JavaScript
- SIEM Source: Wazuh API
- Database: PostgreSQL
- Dashboard Name: Ariba Dashboard
- Initial Scope: Wazuh-based alert dashboard only
- Future Scope: Multi-SIEM, case management, automation, SOAR-style workflows

The system must be developed in phases. Every phase must be clean, secure, documented, and ready for enterprise SOC use.

---

## 2. Main Goal

The main goal is to create a SOC dashboard where analysts can:

1. See incoming Wazuh alerts.
2. Understand alert severity, status, verdict, assignee, and evidence.
3. Assign alerts to themselves or other analysts.
4. Move alerts through the triage lifecycle.
5. Add analyst comments and investigation notes.
6. Mark alerts as True Positive, False Positive, Benign Positive, or Pending.
7. Escalate serious alerts to L2 or management.
8. Close resolved alerts with clear reason and evidence.
9. Generate management reports.
10. Track SOC performance, SLA, alert volume, and analyst activity.

---

## 3. SOC Role Understanding

### 3.1 SOC L1 Analyst

SOC L1 analysts are the first line of defense. They work with alerts every day and are responsible for initial triage.

L1 responsibilities:

- Review new alerts.
- Pick up unassigned alerts.
- Move alerts from New to In Progress.
- Check alert details, host, user, source IP, process, command line, rule name, and event evidence.
- Decide whether the alert is suspicious or harmless.
- Add investigation comments.
- Mark obvious noise as False Positive if allowed by policy.
- Escalate real threats or unclear alerts to L2.
- Close alerts only when closure rules are satisfied.

L1 must not ignore alerts. Every alert must have status, assignee, analyst note, and final verdict before closure.

### 3.2 SOC L2 Analyst

SOC L2 analysts receive escalated alerts from L1 and perform deeper analysis.

L2 responsibilities:

- Review escalated alerts.
- Validate whether the alert is a real threat.
- Perform deeper investigation.
- Review related events, indicators, host activity, user behavior, network evidence, and timeline.
- Recommend containment, eradication, and remediation.
- Confirm True Positive or False Positive verdict.
- Escalate to Incident Response or SOC Manager when needed.
- Provide final technical notes before closure.

### 3.3 SOC Engineer

SOC Engineers ensure the detection system and dashboard work properly.

SOC Engineer responsibilities:

- Integrate Wazuh API.
- Maintain alert ingestion jobs.
- Tune Wazuh rules.
- Ensure alerts contain enough useful fields for triage.
- Maintain severity mapping.
- Build dashboards, APIs, and reports.
- Ensure database performance and secure storage.
- Add new alert parsers when Wazuh alert format changes.
- Maintain RBAC and audit logs.

### 3.4 SOC Manager

SOC Manager tracks quality, speed, and operational performance.

SOC Manager responsibilities:

- View management dashboards.
- Track open, closed, overdue, and escalated alerts.
- Track analyst workload.
- Track SLA compliance.
- Track True Positive and False Positive rates.
- Review daily, weekly, and monthly reports.
- Ensure real attacks are not missed.
- Approve severity changes and closure policy if required.

---

## 4. Alert Lifecycle

The dashboard must support a complete alert lifecycle.

### 4.1 Alert Status Values

Required statuses:

1. **New**
   - Alert is received from Wazuh.
   - No analyst has started work.
   - Assignee may be empty.

2. **Assigned**
   - Alert has an owner.
   - Work may not have started yet.

3. **In Progress**
   - Analyst is actively investigating.
   - Analyst must add notes before closing.

4. **Escalated**
   - L1 escalated the alert to L2 or manager.
   - Escalation reason is mandatory.

5. **Pending User / Pending IT / Pending Evidence**
   - Investigation is waiting for user, IT team, endpoint team, network team, or additional evidence.

6. **Resolved / Closed**
   - Alert triage is completed.
   - Verdict is mandatory.
   - Closing comment is mandatory.

7. **Archived**
   - Old closed alert moved to archive view.
   - Must remain searchable for reporting and audit.

### 4.2 Alert Verdict Values

Required verdicts:

1. **None**
   - Default value before investigation.

2. **True Positive**
   - Real threat or confirmed malicious/suspicious activity.

3. **False Positive**
   - No threat; alert was triggered incorrectly or expected behavior.

4. **Benign Positive**
   - Alert is technically correct but activity is authorized or acceptable.

5. **Suspicious / Needs Review**
   - Not enough evidence yet.

6. **Duplicate**
   - Same alert already handled in another case.

7. **Test Activity**
   - Internal test, simulation, or authorized security validation.

---

## 5. Alert Properties

Each alert must contain the following core properties.

| No. | Property | Description | Example |
|---|---|---|---|
| 1 | Alert Time | Time when alert was created in Wazuh/dashboard | Mar 21, 2025 at 13:58 |
| 2 | Event Time | Time when original event happened | Mar 21, 2025 at 13:55 |
| 3 | Alert Name | Rule name or summarized title | Windows RDP Bruteforce |
| 4 | Severity | Urgency level | Low, Medium, High, Critical |
| 5 | Status | Current workflow stage | New, In Progress, Closed |
| 6 | Verdict | Analyst classification | True Positive, False Positive |
| 7 | Assignee | Analyst responsible for alert | J.Adams (L2) |
| 8 | Description | Explanation of alert logic and risk | Detects double extension file |
| 9 | Alert Fields | Technical evidence fields | Hostname, username, source IP, process |
| 10 | Source | Alert source | Wazuh, Sysmon, Windows Event, Linux Audit |
| 11 | Rule ID | Wazuh rule ID | 5712 |
| 12 | Agent ID | Wazuh agent ID | 009 |
| 13 | Agent Name | Endpoint/server name | LPT-HR-009 |
| 14 | MITRE Mapping | Tactic and technique | T1110 Brute Force |
| 15 | Analyst Comment | Investigation note | User confirmed activity was not expected |
| 16 | Closure Reason | Why alert was closed | Confirmed false positive |
| 17 | Escalation Reason | Why L1 escalated | Possible credential compromise |
| 18 | Created By | System or user who created record | Wazuh API sync |
| 19 | Updated By | Last analyst who updated alert | L1 analyst |
| 20 | Audit Trail | Full change history | Status changed from New to In Progress |

---

## 6. Alert Severity

Severity must be understandable for SOC and management.

### 6.1 Severity Levels

| Severity | Meaning | Example |
|---|---|---|
| Low | Informational or low-risk alert | Download from GitHub repository |
| Medium | Needs review, moderate risk | Unusual VPN login location |
| High | Serious suspicious activity | Double-extension file creation |
| Critical | Urgent possible compromise | Potential data exfiltration |

### 6.2 Severity Color Mapping

- Low: Green
- Medium: Yellow
- High: Orange
- Critical: Red

### 6.3 Severity Change Rule

Analysts may change severity only when allowed by role permission.

When severity is changed, the system must store:

- Old severity
- New severity
- Changed by
- Changed time
- Reason for change

---

## 7. Alert Prioritisation

The dashboard must help analysts prioritize alerts.

### 7.1 Priority Factors

Alert priority should be based on:

- Severity
- Asset criticality
- User privilege level
- Alert age
- Repeated alerts from same host/user/IP
- MITRE technique risk
- Whether the alert involves external IP
- Whether the alert involves admin account
- Whether the alert involves malware, credential theft, lateral movement, exfiltration, or persistence
- Business impact
- SLA deadline

### 7.2 Suggested Priority Logic

Critical priority when:

- Severity is Critical
- Data exfiltration is suspected
- Domain admin or privileged user is involved
- Malware execution is confirmed
- Mimikatz, credential dumping, ransomware behavior, or lateral movement is detected

High priority when:

- Severity is High
- Suspicious process execution
- Brute force with successful login
- Unauthorized remote access
- Suspicious PowerShell or script activity

Medium priority when:

- Unusual login
- Repeated failed login
- Suspicious but incomplete evidence

Low priority when:

- Informational activity
- Known expected activity
- Test activity
- Low-risk policy alert

---

## 8. Alert Triage Workflow

### 8.1 Standard L1 Triage Flow

1. Analyst opens dashboard.
2. Analyst checks New alerts.
3. Analyst picks one alert.
4. System assigns alert to analyst.
5. Status changes to In Progress.
6. Analyst reviews alert details.
7. Analyst checks related events.
8. Analyst adds comment.
9. Analyst chooses verdict.
10. Analyst closes alert or escalates to L2.

### 8.2 Required Before Closing Alert

The system must not allow alert closure unless these fields are present:

- Assignee
- Status
- Verdict
- Analyst comment
- Closure reason
- Last updated time

For True Positive closure, the system must also require:

- Impact summary
- Affected asset
- Action taken
- Escalation or incident reference if applicable

For False Positive closure, the system must require:

- Why it is false positive
- Evidence source
- Recommendation for rule tuning if needed

### 8.3 Escalation Flow

L1 can escalate to L2 when:

- Alert is Critical
- Alert involves privileged account
- Alert involves production server
- Malware is suspected
- Data exfiltration is suspected
- L1 cannot determine verdict
- Repeated alert pattern is observed

Escalation must require:

- Escalation reason
- Current investigation summary
- Evidence checked
- Suggested next action

---

## 9. Alert Funnel

The dashboard must show alert funnel for management.

Example funnel:

1. Total alerts received
2. New alerts
3. Assigned alerts
4. In Progress alerts
5. Escalated alerts
6. Closed alerts
7. True Positive alerts
8. False Positive alerts
9. Benign Positive alerts
10. Archived alerts

Management must see conversion rate between each stage, such as:

- Total alerts vs closed alerts
- Total alerts vs true positives
- New alerts older than SLA
- False positive ratio
- Escalation ratio

---

## 10. Dashboard Views

### 10.1 Board View

Board view should work like a SOC Kanban board.

Columns:

- New
- In Progress
- True Positives
- False Positives
- Escalated
- Pending
- Archive

Each card must show:

- Alert name
- Created time
- Severity
- Source
- Assignee
- Quick action button

Card colors:

- Critical: red accent
- High: orange accent
- Medium: yellow accent
- Low: green accent
- False Positive column: green background
- True Positive column: red/pink background

### 10.2 Table View

Table view is for analysts and managers.

Required columns:

1. Time
2. Alert Name
3. Severity
4. Status
5. Verdict
6. Assignee
7. Source
8. Host
9. Rule ID
10. MITRE Technique
11. SLA Status
12. Actions

Table functions:

- Search alert
- Sort by time, severity, status, verdict, assignee
- Filter by severity
- Filter by status
- Filter by verdict
- Filter by assignee
- Filter by source
- Filter by date range
- Expand row to see full alert details
- Edit alert
- Assign alert
- Export report

### 10.3 Alert Detail View

Alert detail page must show full evidence.

Sections:

- Summary
- Status and assignment
- Alert description
- Wazuh rule details
- Agent details
- Host details
- User details
- Process details
- Network details
- File details
- MITRE ATT&CK mapping
- Raw Wazuh alert JSON
- Analyst comments
- Timeline
- Related alerts
- Audit history

### 10.4 Edit Alert Modal

Edit modal must include:

- Assignee dropdown
- Status dropdown
- Severity dropdown
- Verdict dropdown
- Analyst comment text area
- Save button
- Cancel/close button

Validation:

- Analyst comment required when changing status to Closed.
- Verdict required when changing status to Closed.
- Escalation reason required when changing status to Escalated.
- Severity change reason required when severity is changed.

---

## 11. Management Dashboard

The management dashboard must provide high-level visibility.

### 11.1 KPI Cards

Required KPI cards:

- Total alerts today
- New alerts
- In Progress alerts
- Critical alerts
- High alerts
- Escalated alerts
- Closed alerts
- True positives
- False positives
- Average triage time
- SLA breached alerts
- Alerts by analyst

### 11.2 Charts

Required charts:

- Alerts by severity
- Alerts by status
- Alerts by verdict
- Alerts by source
- Alerts over time
- Top 10 alert names
- Top 10 affected hosts
- Top 10 affected users
- True positive vs false positive trend
- Analyst workload
- SLA compliance chart

### 11.3 Manager Filters

Filters:

- Date range
- Severity
- Status
- Verdict
- Assignee
- Department
- Host group
- Wazuh agent group
- Alert source

### 11.4 Management Report Summary

Management must be able to see:

- How many alerts came today/this week/this month
- Which alerts are still open
- Which critical alerts are unresolved
- Which analysts are overloaded
- Which assets are most targeted
- Which alert rules generate too many false positives
- Mean time to acknowledge
- Mean time to resolve
- SLA breach count

---

## 12. Reporting Guide

The system must support report generation.

### 12.1 Daily SOC Report

Daily report should include:

- Total alerts received
- Open alerts
- Closed alerts
- Critical and high alerts
- True positives
- False positives
- Escalated alerts
- Major incidents
- Top affected hosts
- Top alert categories
- Analyst activity
- SLA breaches
- Pending actions

### 12.2 Weekly SOC Report

Weekly report should include:

- Weekly alert trend
- Severity distribution
- True positive and false positive trend
- Top recurring alerts
- Top risky assets
- Rule tuning recommendations
- SOC workload summary
- Escalation summary
- Management recommendations

### 12.3 Monthly SOC Report

Monthly report should include:

- Executive summary
- SOC performance overview
- Threat trend
- Alert funnel
- Incident summary
- SLA performance
- Analyst productivity
- Top MITRE techniques
- Top departments affected
- Improvement plan

### 12.4 Export Formats

Required export formats:

- PDF
- Excel
- CSV
- HTML print view

---

## 13. Escalation Guide

### 13.1 Escalate to L2 When

- Alert is Critical.
- Alert involves admin account.
- Alert involves server, database, ERP, HRM, email, firewall, VPN, or domain controller.
- Malware execution is suspected.
- Credential dumping is suspected.
- Data exfiltration is suspected.
- Brute force is followed by successful login.
- Multiple hosts are affected.
- Same alert repeats frequently.
- Analyst is unsure.

### 13.2 Escalation Fields

Escalation form must include:

- Escalated to
- Escalation reason
- Investigation summary
- Evidence collected
- Risk assessment
- Recommended next action
- Attachments if needed

### 13.3 Escalation Notification

Future notification options:

- Email
- Microsoft Teams
- Slack
- SMS
- Dashboard notification

Initial phase can use dashboard notification only.

---

## 14. SOC Communication

The dashboard must help SOC communication.

### 14.1 Analyst Comments

Every alert must allow threaded comments.

Comment fields:

- Comment text
- Comment type
- Created by
- Created time
- Visibility

Comment types:

- Investigation note
- Escalation note
- Closure note
- Manager review note
- Rule tuning note

### 14.2 Communication Rules

- Comments must not be deleted permanently.
- Edited comments must keep edit history.
- System-generated comments must be separate from analyst comments.
- Every status change must create a timeline entry.

---

## 15. Wazuh API Integration

### 15.1 Purpose

The system must collect alerts from Wazuh API and store them in PostgreSQL for workflow management.

Wazuh is the alert source. Ariba Dashboard is the triage and management layer.

### 15.2 Data Collection

The backend should use scheduled jobs to fetch alerts from Wazuh.

Required approach:

- Connect to Wazuh API securely.
- Fetch alerts by time range.
- Avoid duplicate alerts.
- Store raw JSON.
- Normalize important fields into database columns.
- Keep sync status and error logs.

### 15.3 Required Wazuh Fields to Capture

Capture these fields when available:

- Wazuh alert ID
- Timestamp
- Rule ID
- Rule level
- Rule description
- Rule groups
- MITRE tactic
- MITRE technique
- Agent ID
- Agent name
- Agent IP
- Manager name
- Full log
- Decoder name
- Location
- Source IP
- Destination IP
- Source port
- Destination port
- Username
- Hostname
- Process name
- Command line
- File path
- File hash MD5
- File hash SHA1
- File hash SHA256
- Windows event ID
- Linux audit key
- Raw alert JSON

### 15.4 Severity Mapping from Wazuh

Suggested mapping:

- Wazuh level 0–3: Low
- Wazuh level 4–7: Medium
- Wazuh level 8–11: High
- Wazuh level 12–15: Critical

The mapping must be configurable from admin settings.

### 15.5 Sync Job

Required sync features:

- Manual sync button
- Scheduled sync every few minutes
- Last successful sync time
- Last failed sync time
- Sync error log
- Duplicate prevention by Wazuh alert ID
- Retry mechanism

---

## 16. PostgreSQL Database Design

### 16.1 Main Tables

Required tables:

1. users
2. roles
3. permissions
4. alerts
5. alert_details
6. alert_comments
7. alert_status_history
8. alert_assignments
9. alert_escalations
10. alert_raw_events
11. alert_related_events
12. alert_reports
13. wazuh_sync_logs
14. audit_logs
15. notification_logs
16. system_settings

### 16.2 Alerts Table Important Columns

alerts table should include:

- id
- wazuh_alert_id
- alert_time
- event_time
- name
- description
- severity
- status
- verdict
- source
- rule_id
- rule_level
- agent_id
- agent_name
- agent_ip
- hostname
- username
- source_ip
- destination_ip
- process_name
- command_line
- file_path
- file_hash_md5
- file_hash_sha1
- file_hash_sha256
- mitre_tactic
- mitre_technique
- assignee_id
- assigned_at
- acknowledged_at
- escalated_at
- closed_at
- closure_reason
- sla_due_at
- sla_status
- raw_json
- created_at
- updated_at

### 16.3 Audit Logs

Every important action must be logged:

- Alert created
- Alert assigned
- Status changed
- Severity changed
- Verdict changed
- Comment added
- Alert escalated
- Alert closed
- Report generated
- User login
- User logout
- Permission changed

Audit log fields:

- actor user
- action name
- object type
- object ID
- old value
- new value
- IP address
- user agent
- timestamp

---

## 17. User Roles and Permissions

### 17.1 Required Roles

- Admin
- SOC Manager
- SOC Engineer
- SOC L2 Analyst
- SOC L1 Analyst
- Viewer / Management Viewer

### 17.2 Permission Matrix

| Feature | L1 | L2 | Engineer | Manager | Admin |
|---|---|---|---|---|---|
| View alerts | Yes | Yes | Yes | Yes | Yes |
| Assign self | Yes | Yes | Yes | Yes | Yes |
| Assign others | No | Yes | No | Yes | Yes |
| Change status | Yes | Yes | No | Yes | Yes |
| Change severity | Limited | Yes | Yes | Yes | Yes |
| Change verdict | Yes | Yes | No | Yes | Yes |
| Close alert | Yes, with rule | Yes | No | Yes | Yes |
| Escalate alert | Yes | Yes | No | Yes | Yes |
| View reports | Limited | Yes | Yes | Yes | Yes |
| Manage users | No | No | No | Limited | Yes |
| Manage Wazuh settings | No | No | Yes | No | Yes |
| View audit logs | No | Limited | Yes | Yes | Yes |

---

## 18. Security Requirements

The dashboard must follow enterprise security standards.

Required controls:

- Login required for all pages.
- Role-based access control.
- Strong password policy.
- Optional MFA in future phase.
- CSRF protection enabled.
- Secure session settings.
- HTTPS only in production.
- Secure cookies.
- Input validation.
- Output encoding.
- SQL injection prevention using Django ORM.
- XSS prevention.
- Audit logging.
- No raw Wazuh credentials in source code.
- Use environment variables for secrets.
- Database connection over secure network.
- Admin actions logged.
- Sensitive data masking where needed.

---

## 19. UI/UX Requirements

The dashboard should be dark-themed and SOC-friendly.

### 19.1 Design Style

- Dark background
- Clear table layout
- Severity color badges
- Status pills
- Verdict pills
- Analyst-friendly spacing
- Fast search
- Expandable alert details
- Modal edit form
- Board and table toggle
- Management dashboard view

### 19.2 Required Pages

1. Login page
2. Main alert dashboard
3. Board view
4. Table view
5. Alert detail page
6. Management dashboard
7. Reports page
8. Escalation page
9. Analyst performance page
10. Wazuh sync status page
11. User management page
12. Role and permission page
13. Settings page
14. Audit log page

---

## 20. Development Phases

### Phase 1 — Project Foundation

Deliverables:

- Django project setup
- PostgreSQL connection
- Base template
- Login/logout
- User roles
- Static files
- Environment configuration
- Basic dashboard layout

### Phase 2 — Alert Model and Manual Data

Deliverables:

- Alert database models
- Admin panel support
- Sample alert seed data
- Table view
- Board view
- Alert detail view
- Edit alert modal

### Phase 3 — Alert Workflow

Deliverables:

- Assign alert
- Change status
- Change severity
- Change verdict
- Add comments
- Close alert with validation
- Escalate alert
- Audit history
- Timeline

### Phase 4 — Wazuh API Integration

Deliverables:

- Wazuh API settings
- Authentication to Wazuh
- Alert fetch service
- Alert normalization
- Duplicate prevention
- Scheduled sync job
- Sync logs
- Manual sync button

### Phase 5 — Management Dashboard

Deliverables:

- KPI cards
- Charts
- Alert funnel
- SLA tracking
- Analyst workload
- Date filters
- Severity/status/verdict filters

### Phase 6 — Reporting

Deliverables:

- Daily report
- Weekly report
- Monthly report
- PDF export
- Excel export
- CSV export
- Printable HTML report

### Phase 7 — Enterprise Hardening

Deliverables:

- Full RBAC
- Security hardening
- Audit log review
- Performance optimization
- Pagination
- Background jobs
- Error handling
- Backup strategy
- Deployment guide

### Phase 8 — Future Enhancement

Possible future features:

- Case management
- Incident management
- Playbooks
- Email notification
- Teams notification
- SMS alert
- SOAR automation
- Threat intelligence enrichment
- Asset criticality integration
- AD/LDAP login
- Multi-SIEM support
- TheHive/MISP integration

---

## 21. Sample Alert Types

The system must support alert examples like:

- Windows RDP Bruteforce
- Potential Data Exfiltration
- Unusual Gmail Login Location
- Email Marked as Phishing
- Email Marked as Spam
- Unapproved Mimikatz Usage
- Adware Infection of PC-1273
- Double-Extension File Creation
- Download from GitHub Repository
- Unusual VPN Login Location
- Bruteforce Attack from External
- Suspicious PowerShell Command
- Linux SSH Brute Force
- Malware Hash Detected
- Admin Login from New Location
- Multiple Failed Login Attempts

---

## 22. Example Alert Detail Fields

Example for Double-Extension File Creation:

- Description: This rule detects creation of a double-extension file like `*.pdf.exe` or `*.gif.lnk`, often used by attackers in phishing attacks.
- Host: LPT-HR-009
- Process Name: chrome.exe
- Process User: S.Conway
- Target File: C:\Users\S.Conway\Downloads\cats2025.mp4.exe
- File MotW: https://freecatvideoshd.monster/cats2025.mp4.exe
- File MD5: 14d8486f3f63875ef93cfd240c5dc10b

---

## 23. Alert Resolution Rules

Alert resolution must be controlled.

### 23.1 False Positive Resolution

Required before save:

- Verdict = False Positive
- Status = Closed
- Analyst comment
- Reason why not malicious
- Evidence checked
- Optional rule tuning recommendation

### 23.2 True Positive Resolution

Required before save:

- Verdict = True Positive
- Status = Closed or Escalated
- Analyst comment
- Affected asset
- Confirmed evidence
- Action taken
- Escalation or incident reference if needed

### 23.3 Duplicate Resolution

Required before save:

- Verdict = Duplicate
- Linked alert ID or case ID
- Analyst comment

---

## 24. SLA Requirements

The dashboard must track SLA.

Suggested SLA:

| Severity | Acknowledge SLA | Resolve SLA |
|---|---:|---:|
| Critical | 15 minutes | 4 hours |
| High | 30 minutes | 8 hours |
| Medium | 2 hours | 24 hours |
| Low | 8 hours | 72 hours |

SLA status:

- Within SLA
- Near SLA breach
- Breached

---

## 25. Search and Filter Requirements

Analysts must be able to search by:

- Alert name
- Hostname
- Username
- Source IP
- Destination IP
- Process name
- File hash
- Rule ID
- Agent name
- MITRE technique
- Assignee

Filters:

- Date range
- Severity
- Status
- Verdict
- Assignee
- Source
- Agent group
- SLA status

---

## 26. Notifications

Initial phase:

- Dashboard notification only

Future phase:

- Email notification
- Teams notification
- SMS notification
- Escalation notification
- SLA breach notification
- New critical alert notification

Notification events:

- New Critical alert
- Alert assigned
- Alert escalated
- Alert closed
- SLA breached
- Comment added

---

## 27. Non-Functional Requirements

The system must be:

- Fast
- Secure
- Searchable
- Auditable
- Easy for L1 analysts
- Useful for managers
- Scalable for large alert volume
- Easy to integrate with Wazuh
- Easy to maintain
- Cleanly documented

Performance requirements:

- Dashboard loads quickly.
- Table uses pagination.
- Large raw JSON must not slow down table view.
- Index important database columns.
- Background jobs handle Wazuh sync.

---

## 28. Deployment Requirements

Production deployment should include:

- Linux server
- Python virtual environment
- PostgreSQL
- Gunicorn
- Nginx
- HTTPS certificate
- Environment variables
- Log directory
- Backup plan
- Systemd service
- Firewall rules

Required environment variables:

- DJANGO_SECRET_KEY
- DJANGO_DEBUG
- DJANGO_ALLOWED_HOSTS
- DATABASE_NAME
- DATABASE_USER
- DATABASE_PASSWORD
- DATABASE_HOST
- DATABASE_PORT
- WAZUH_API_URL
- WAZUH_API_USER
- WAZUH_API_PASSWORD
- WAZUH_VERIFY_SSL

---

## 29. Code Quality Rules for AI Developer

When generating code for this project, AI must follow these rules:

1. Use Django best practices.
2. Use PostgreSQL-compatible models.
3. Do not hardcode secrets.
4. Keep apps separated.
5. Use services for Wazuh API logic.
6. Use templates for UI.
7. Use forms for validation.
8. Use class-based or clean function-based views consistently.
9. Add comments only where useful.
10. Keep security first.
11. Add audit logging for every workflow change.
12. Avoid destructive actions without confirmation.
13. Keep database migrations clean.
14. Use pagination for alert table.
15. Use reusable template components for badges, cards, filters, and modals.

---

## 30. Suggested Django App Structure

Recommended apps:

```text
ariba_dashboard/
  config/
  accounts/
  alerts/
  wazuh_integration/
  reports/
  management_dashboard/
  audit/
  notifications/
  templates/
  static/
```

Recommended folders:

```text
alerts/
  models.py
  views.py
  forms.py
  services.py
  filters.py
  urls.py
  admin.py
  tests.py

wazuh_integration/
  client.py
  services.py
  tasks.py
  parsers.py
  models.py

reports/
  services.py
  exporters.py
  views.py
```

---

## 31. Acceptance Criteria

The project is successful when:

- Wazuh alerts are visible in dashboard.
- Analysts can assign, triage, escalate, and close alerts.
- Alert status and verdict are tracked.
- Alert details and raw Wazuh data are available.
- Management can see KPI dashboard.
- Reports can be generated.
- All actions are audited.
- Role permissions work correctly.
- PostgreSQL stores all workflow data.
- Dashboard is usable by L1 analysts.
- SOC manager can track speed and quality of alert triage.

---

## 32. Final Instruction to AI Developer

Build this project step by step. Do not skip the SOC workflow. Do not build only a simple alert table. The dashboard must support real SOC operations:

- Alert ingestion
- Alert triage
- Assignment
- Escalation
- Verdict
- Resolution
- Reporting
- Management visibility
- Audit history

The first production version must focus only on **Wazuh-based alert management** using **Python Django, Django templates, PostgreSQL, and Wazuh API**.
