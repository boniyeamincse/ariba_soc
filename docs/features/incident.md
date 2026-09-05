Continue working on the existing Django project `ariba_soc`.

Feature 01 — Live Search should already be implemented.

Implement only one new feature in this task:

# Feature 02 — Incident Management Core

Do not implement AI analysis, automatic alert correlation, SOAR, Active Response, advanced forensics, or scheduled reporting in this task.

First inspect:

```text
alerts/models.py
alerts/views.py
alerts/workflow.py
accounts/models.py
accounts/permissions.py
dashboard/
audit/
hunting/
templates/base.html
config/settings.py
config/urls.py
```

Preserve existing alert, L1/L2/L3 workflow, assignment, escalation, comment, SLA, and audit functionality.

## Objective

Authorized analysts must be able to:

* Create an incident from one or more existing alerts.
* Link additional alerts to an incident.
* Assign an incident owner and response team.
* Move an incident through a controlled lifecycle.
* Add investigation notes.
* Track containment, eradication and recovery.
* View an immutable incident timeline.
* Close or reopen an incident with mandatory evidence.

An Incident is not another Alert status. Create a separate `Incident` entity.

Required relationship:

```text
One Incident
    ↓
Many linked Alerts
```

## 1. Create application

Run:

```bash
python manage.py startapp incidents
```

Create:

```text
incidents/
├── __init__.py
├── apps.py
├── models.py
├── forms.py
├── permissions.py
├── selectors.py
├── workflow.py
├── urls.py
├── views/
│   ├── __init__.py
│   ├── list.py
│   ├── detail.py
│   ├── create.py
│   ├── assignment.py
│   ├── transition.py
│   └── notes.py
├── services/
│   ├── __init__.py
│   ├── incident_creator.py
│   ├── alert_linker.py
│   ├── timeline.py
│   └── metrics.py
├── templates/incidents/
│   ├── incident_list.html
│   ├── incident_create.html
│   ├── incident_detail.html
│   └── partials/
│       ├── _incident_header.html
│       ├── _linked_alerts.html
│       ├── _timeline.html
│       ├── _notes.html
│       └── _transition_actions.html
├── static/incidents/
│   ├── css/incidents.css
│   └── js/incidents.js
├── migrations/
└── tests/
```

Add to `INSTALLED_APPS`:

```python
"incidents",
```

Add to `config/urls.py`:

```python
path("incidents/", include("incidents.urls")),
```

## 2. Incident model

Add:

```python
class Incident(models.Model):
    STATUS_CHOICES = [
        ("NEW", "New"),
        ("CONFIRMED", "Confirmed"),
        ("INVESTIGATING", "Investigating"),
        ("CONTAINMENT", "Containment"),
        ("ERADICATION", "Eradication"),
        ("RECOVERY", "Recovery"),
        ("MONITORING", "Monitoring"),
        ("RESOLVED", "Resolved"),
        ("CLOSED", "Closed"),
        ("REOPENED", "Reopened"),
    ]

    SEVERITY_CHOICES = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
        ("CRITICAL", "Critical"),
    ]

    incident_number
    title
    description
    severity
    status
    priority
    owner
    response_team
    created_by
    business_unit
    affected_service
    business_impact
    detection_source
    current_tier
    version
    detected_at
    declared_at
    contained_at
    eradicated_at
    recovered_at
    resolved_at
    closed_at
    created_at
    updated_at
```

Requirements:

* Use a database-safe unique incident number.
* Example: `INC-2026-000001`.
* Do not generate the sequence using `count() + 1`.
* Use a database sequence, locked counter or UUID-backed safe mechanism.
* `owner`, `created_by` and other user references must preserve history using `PROTECT` or `SET_NULL`.
* Add indexes for incident number, status, severity, owner, response team, detected time and created time.
* Add a `version` field for optimistic concurrency.

## 3. Link alerts to incidents

Create:

```python
class IncidentAlert(models.Model):
    incident
    alert
    linked_by
    link_reason
    is_primary
    linked_at
```

Constraints:

* The same alert cannot be linked twice to the same incident.
* An incident must have only one primary alert.
* Do not delete the original alert.
* Do not copy the complete alert into the Incident table.
* Preserve the relationship and alert history.
* Linking and unlinking must create timeline and audit events.
* Closed incidents cannot accept new alerts unless reopened.
* Unlinking the primary alert requires another primary alert to be selected.
* At least one linked alert must remain.

## 4. Incident timeline

Create:

```python
class IncidentTimeline(models.Model):
    EVENT_TYPE_CHOICES = [
        ("CREATED", "Created"),
        ("ALERT_LINKED", "Alert Linked"),
        ("ALERT_UNLINKED", "Alert Unlinked"),
        ("ASSIGNED", "Assigned"),
        ("STATUS_CHANGED", "Status Changed"),
        ("SEVERITY_CHANGED", "Severity Changed"),
        ("NOTE_ADDED", "Note Added"),
        ("CONTAINED", "Contained"),
        ("ERADICATED", "Eradicated"),
        ("RECOVERED", "Recovered"),
        ("RESOLVED", "Resolved"),
        ("CLOSED", "Closed"),
        ("REOPENED", "Reopened"),
    ]

    incident
    event_type
    actor
    actor_role
    title
    description
    from_value
    to_value
    metadata
    request_id
    created_at
```

Timeline events must be append-only through normal application operations.

Do not allow timeline events to be edited or deleted through ordinary UI.

Never store passwords, tokens, cookies, API keys or other credentials in timeline metadata.

## 5. Incident notes

Create:

```python
class IncidentNote(models.Model):
    NOTE_TYPES = [
        ("INVESTIGATION", "Investigation"),
        ("CONTAINMENT", "Containment"),
        ("ERADICATION", "Eradication"),
        ("RECOVERY", "Recovery"),
        ("MANAGEMENT", "Management"),
        ("LESSON_LEARNED", "Lesson Learned"),
    ]

    incident
    note_type
    note
    created_by
    created_at
```

Rules:

* Notes must be append-only.
* Normal users cannot edit or delete previously submitted notes.
* Render all note content safely.
* Never trust HTML submitted by users.
* Record a timeline event when a note is added.

## 6. Permissions

Add:

```text
can_view_incidents
can_create_incident
can_assign_incident
can_manage_incident
can_close_incident
can_reopen_incident
can_link_incident_alerts
```

Default matrix:

| Role    |                  View |  Create |  Assign |  Manage | Close |  Reopen | Link alerts |
| ------- | --------------------: | ------: | ------: | ------: | ----: | ------: | ----------: |
| L1      |               Limited |      No |      No |      No |    No |      No |          No |
| L2      |                   Yes |     Yes | Limited |     Yes |    No |      No |         Yes |
| L3      |                   Yes |     Yes |     Yes |     Yes |   Yes | Limited |         Yes |
| SOC_ENG |                   Yes | Limited |      No | Limited |    No |      No |         Yes |
| SOC_MGR |                   Yes |     Yes |     Yes |     Yes |   Yes |     Yes |         Yes |
| ADMIN   |                   Yes |     Yes |     Yes |     Yes |   Yes |     Yes |         Yes |
| VIEWER  |  Read-only if granted |      No |      No |      No |    No |      No |          No |
| MONITOR | Aggregated count only |      No |      No |      No |    No |      No |          No |

L1 may view only incidents containing alerts visible to them and only when policy permits.

Every list, detail and action must enforce backend and object-level authorization.

Create:

```python
get_visible_incidents(user)
```

All incident queries must use this selector to prevent IDOR.

## 7. Create incident from alert

Add to an authorized alert detail page:

```text
Create Incident
```

Allowed roles:

```text
L2
L3
SOC_MGR
ADMIN
```

Required fields:

```text
Title
Description
Severity
Priority
Business unit
Affected service
Business impact
Response team
Owner
Declaration reason
```

Creation must:

1. Verify that the actor can see the alert.
2. Verify `can_create_incident`.
3. Lock the alert.
4. Create the Incident.
5. Link the alert as primary.
6. Set `declared_at`.
7. Add a `CREATED` timeline event.
8. Add an `ALERT_LINKED` timeline event.
9. Create security audit events.
10. Mark the alert as an incident candidate/linked without destroying its existing workflow history.
11. Send notification to the owner and response team.

Run the operation inside:

```python
transaction.atomic()
```

## 8. Create incident from multiple alerts

On the authorized alert list and Live Search result:

```text
Create Incident from Selected Alerts
```

Rules:

* The actor must have access to every selected alert.
* At least one alert is required.
* Limit the number of alerts per request.
* One selected alert must be marked primary.
* Duplicate alert IDs must be rejected or safely deduplicated.
* If any alert is unauthorized, reject the entire operation.
* Do not partially create an incident.
* Use `transaction.atomic()` and row locking.

For a Live Search Wazuh result not yet stored in PostgreSQL:

* Do not link raw browser JSON.
* Resolve the Wazuh event by trusted server-side ID.
* Import it into the existing Alert model safely.
* Then link the resulting Alert.
* Revalidate that the event belongs to the approved Wazuh index.

## 9. Incident lifecycle

Allowed transitions:

```text
NEW → CONFIRMED
NEW → CLOSED

CONFIRMED → INVESTIGATING
CONFIRMED → CLOSED

INVESTIGATING → CONTAINMENT
INVESTIGATING → RESOLVED

CONTAINMENT → ERADICATION
CONTAINMENT → INVESTIGATING

ERADICATION → RECOVERY
ERADICATION → CONTAINMENT

RECOVERY → MONITORING
RECOVERY → ERADICATION

MONITORING → RESOLVED
MONITORING → RECOVERY

RESOLVED → CLOSED
RESOLVED → REOPENED

CLOSED → REOPENED

REOPENED → INVESTIGATING
```

Do not allow arbitrary status changes.

Create workflow functions in:

```text
incidents/workflow.py
```

For example:

```python
confirm_incident()
start_investigation()
start_containment()
mark_eradicated()
start_recovery()
start_monitoring()
resolve_incident()
close_incident()
reopen_incident()
```

Every transition must:

* Use `transaction.atomic()`.
* Lock the Incident with `select_for_update()`.
* Verify the expected `version`.
* Validate actor permissions.
* Validate the current state.
* Require appropriate evidence/reason.
* Update lifecycle timestamp.
* Increment the version.
* Create a timeline event.
* Create an audit event.
* Send required notifications.
* Return HTTP 409 for invalid or stale transitions.

## 10. Mandatory transition information

### Containment

Require:

```text
Containment action
Affected assets
Action owner
Containment time
Verification note
```

### Eradication

Require:

```text
Root cause
Removed artifact/account/process
Eradication action
Verification method
```

### Recovery

Require:

```text
Recovered systems
Service validation
Monitoring requirement
Business owner confirmation
```

### Resolution

Require:

```text
Resolution summary
Root cause summary
Impact summary
Remediation summary
Residual risk
```

### Closure

Require:

```text
Final classification
Closure reason
Lessons learned
Manager/L3 review
```

### Reopen

Require:

```text
Reopen reason
New evidence
Reopen target owner
```

Do not permit closure without linked alerts and required resolution information.

## 11. Routes

Implement:

```text
GET  /incidents/
GET  /incidents/create/
POST /incidents/create/
GET  /incidents/<incident-number>/
POST /incidents/<incident-number>/assign/
POST /incidents/<incident-number>/transition/
POST /incidents/<incident-number>/notes/
POST /incidents/<incident-number>/alerts/link/
POST /incidents/<incident-number>/alerts/unlink/
POST /alerts/<alert-id>/create-incident/
```

All mutation routes must be POST-only and CSRF protected.

Use incident number or UUID in public URLs, not predictable database IDs alone.

## 12. Incident list page

Display:

```text
Incident number
Title
Severity
Status
Priority
Owner
Response team
Affected service
Linked alert count
Age
Last updated
```

Filters:

```text
Status
Severity
Priority
Owner
Response team
Business unit
Date range
Search
```

Default sorting:

```text
Critical first
Then oldest unresolved incident
```

Add pagination.

## 13. Incident detail page

Display:

* Incident header
* Severity and status
* Owner and response team
* Business impact
* Affected service
* Lifecycle timestamps
* Linked alerts
* Investigation notes
* Containment information
* Eradication information
* Recovery information
* Immutable timeline
* Authorized workflow actions
* Incident age
* Current version

Linked alert table:

```text
Alert ID
Primary
Alert name
Severity
Status
Hostname
Source IP
Assignee
Alert time
Link reason
```

Users may open an alert only if they also have access to that alert.

## 14. Notifications

Generate notifications for:

```text
Incident created
Owner assigned
Response team changed
Critical incident declared
Containment started
Incident resolved
Incident closed
Incident reopened
Alert linked
Alert unlinked
```

Notification failures must be logged.

Do not allow notification failure to roll back an otherwise valid incident transition, but record delivery status for retry.

## 15. Manager and dashboard integration

Add real database metrics:

```text
Open incidents
Critical open incidents
Incidents awaiting containment
Incidents in recovery
Oldest unresolved incident
Incidents closed this month
Mean time to containment
Mean time to resolution
```

Role dashboards:

* L2: incident candidates and incidents owned by L2.
* L3: advanced investigations and active incidents.
* Manager: all incident KPIs.
* Monitor: aggregated incident count only, without sensitive details.

Avoid one query per incident. Use annotations, conditional aggregation and `select_related`.

## 16. Security requirements

* Prevent IDOR.
* Validate every linked Alert against the actor’s visible queryset.
* Escape all user-supplied content.
* Never accept owner, role or team identity without server-side validation.
* Prevent mass assignment.
* Add CSRF protection.
* Add per-user rate limits to mutation actions.
* Add request/correlation IDs.
* Do not include credentials or sensitive raw logs in notification text.
* Do not hard-delete incidents, timeline or history through ordinary UI.
* Do not expose raw exceptions.

## 17. Tests

Add tests for:

* Authorized L2 creates an incident from one alert.
* L1 cannot create an incident.
* Incident number is unique under concurrent creation.
* Multiple alerts can be linked atomically.
* Unauthorized alert linking rejects the entire transaction.
* The same alert cannot be linked twice.
* Only one primary alert is allowed.
* Closed incident cannot accept a new alert.
* Legal lifecycle transitions succeed.
* Illegal transitions return HTTP 409.
* Stale incident version returns HTTP 409.
* Every successful transition creates timeline and audit events.
* Failed transition does not partially update data.
* Required closure information is enforced.
* L3 closes an eligible incident.
* Manager reopens an incident with a reason.
* Viewer cannot modify incidents.
* Monitor cannot access incident details.
* Inactive profile receives HTTP 403.
* Incident list uses object-level scope.
* IDOR attempts are denied.
* User content is safely rendered.
* Dashboard metrics use actual Incident records.
* Tests never contact real Wazuh or AI services.

## 18. Completion checks

Run:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py makemigrations --check
python manage.py check
python manage.py test incidents
python manage.py test
```

Do not ignore failures.

After implementation provide:

1. Changed files.
2. Migration summary.
3. Incident lifecycle transition matrix.
4. Role-permission matrix.
5. Final routes.
6. Example Incident and linked Alert records.
7. Test results.
8. Remaining limitations.

Do not modify `.env`, production credentials, Docker ports, firewall rules, Wazuh users, real certificates, or live infrastructure.
