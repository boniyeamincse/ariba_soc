App responsibility:

accounts
User login
Role management
Analyst profile
alerts
Alert model
Alert table
Alert board
Alert update
Alert assignment
Alert triage
wazuh_integration
Wazuh API client
Alert sync
Agent sync
Rule sync
dashboard
SOC dashboard
Manager dashboard
KPI widgets
reports
PDF/CSV export
Daily alert report
Weekly SOC report
Analyst performance report
audit
Audit log
Activity history
10. Required UI Design

Use Django templates with HTML, CSS, Bootstrap or Tailwind.

Theme:

Dark SOC dashboard theme
Navy/dark background
Card-based UI
Table with dark rows
Severity badges
Status badges
Verdict badges
Clean management view

Required UI components:

Sidebar menu
Top navbar
Alert board
Alert table
Search box
Filter panel
Edit modal
Detail expanded row
Dashboard cards
Charts
Pagination
Toast notifications

Menu items:

Dashboard
Alert Board
Alert Table
Assigned Alerts
Escalated Alerts
Reports
Wazuh Sync
Settings
Audit Logs
11. Reporting Guide

Create reports for SOC management.

Daily SOC Report

Include:

Total alerts
New alerts
Closed alerts
True positives
False positives
Critical alerts
Escalated alerts
Top alert names
Top affected hosts
SLA breached alerts
Analyst workload
Weekly SOC Report

Include:

Alert trend
True positive trend
False positive trend
Critical incident summary
Mean time to acknowledge
Mean time to resolve
Top recurring detections
Detection tuning recommendation
Analyst Performance Report

Include:

Assigned alerts
Closed alerts
Escalated alerts
Average handling time
False positive closure count
True positive escalations
Pending alerts

Export formats:

CSV
Excel
PDF
12. Escalation Guide

Alert should be escalated to L2 when:

Severity is Critical
Malware or credential dumping detected
Mimikatz detected
Lateral movement suspected
Data exfiltration suspected
Multiple failed login attacks
Suspicious PowerShell command
Unknown executable from Downloads folder
Suspicious external IP
L1 is unable to classify
Business-critical host affected

Escalation fields:

escalation_reason
escalated_by
escalated_to
escalated_at
13. Alert Resolution Rules

Before closing alert, system must check:

Verdict selected
Analyst comment added
Required evidence reviewed
Escalation completed if required
Remediation note added for true positive
Closure reason added

Closed alert fields:

closed_by
closed_at
closure_note

Archive should happen after closure.

14. SLA Rules

Suggested SLA:

Critical: acknowledge within 15 minutes, resolve/update within 1 hour
High: acknowledge within 30 minutes, resolve/update within 4 hours
Medium: acknowledge within 2 hours, resolve/update within 1 business day
Low: acknowledge within 1 business day, resolve within 3 business days

Create SLA breach indicator.

Fields:

sla_ack_due
sla_resolve_due
is_sla_breached
15. SOC Communication

Add communication templates.

L1 to L2 Escalation Message

Required information:

Alert name
Severity
Host
User
Time
Evidence
Initial analysis
Reason for escalation
Recommended next step
Manager Summary

Required information:

Total alerts
Open critical alerts
True positive count
False positive count
SLA breach count
Analyst workload
Major incidents
16. Security Requirements

Implement:

Login required
Role-based permissions
CSRF protection
Server-side validation
Audit log for every update
Secure environment variables
No API secret in frontend
Pagination to prevent heavy load
Input sanitization
Safe error handling
HTTPS-ready deployment
Admin-only settings page
17. Development Phases

Build the project phase by phase.

Phase 1: Project Setup
Create Django project
Configure PostgreSQL
Configure static files
Create base template
Create login/logout
Create user roles
Phase 2: Alert Models
Create Alert model
Create AlertComment model
Create AlertAuditLog model
Run migrations
Create test data
Phase 3: Alert Table
Build alert table page
Add search
Add sorting
Add filter
Add pagination
Add expanded row details
Phase 4: Alert Edit Modal
Build edit modal
Update assignee
Update status
Update severity
Update verdict
Add analyst comment
Save audit log
Phase 5: Alert Board
Build Kanban board
Columns: New, In Progress, True Positives, False Positives, Archive
Show alert cards
Add move status logic
Phase 6: Wazuh API
Create Wazuh API client
Authenticate
Fetch alerts
Normalize alerts
Save alerts
Prevent duplicates
Add manual sync button
Phase 7: Management Dashboard
KPI cards
Charts
Alert trend
Severity distribution
Analyst workload
SLA breach view
Phase 8: Reports
Daily report
Weekly report
Analyst report
CSV/PDF export
Phase 9: Security and Audit
Add RBAC checks
Add audit log
Add permission decorators
Add secure settings
Phase 10: Final Testing
Test L1 workflow
Test L2 workflow
Test Manager dashboard
Test Wazuh sync
Test reports
Test audit log
Test SLA logic
18. Sample Alert Data

Create sample alerts:

Windows RDP Bruteforce
Potential Data Exfiltration
Unusual Gmail Login Location
Email Marked as Phishing
Unapproved Mimikatz Usage
Adware Infection of PC-1273
Email Marked as Spam
Double-Extension File Creation
Download from GitHub Repository
Bruteforce Attack from External
19. Expected Final Output

The final system must provide:

Working Django project
PostgreSQL database
Wazuh API integration
Dark SOC dashboard UI
Alert board
Alert table
Alert edit modal
Alert detail view
Role-based access
Audit logs
Management dashboard
Reporting module
Clear README
.env.example
Installation guide
Test data seed command
20. Important Rule for AI Developer

Do not skip any SOC alert workflow.

This dashboard is not only for showing alerts. It must support the full alert triage process:

Detect → Assign → Investigate → Comment → Escalate → Classify → Resolve → Report → Archive

Always write clean, production-ready Django code.

Use PostgreSQL JSONField for raw Wazuh alert data.

Keep the UI simple, dark, professional, and management-friendly.

End of instruction.
