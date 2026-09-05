Continue working on the existing Django project `ariba_soc`.

Implement only one feature in this task:

# Feature 01 —  Live Search

Do not implement Saved Hunts, AI Assistant, Incident Management, scheduled hunting, or SOAR in this task.

First inspect the existing project, especially:

```text
config/settings.py
config/urls.py
accounts/models.py
wazuh_integration/services.py
wazuh_integration/models.py
alerts/models.py
templates/base.html
```

Reuse the existing secure Wazuh Indexer connection. Do not create another Indexer credential store.

## Objective

Authorized SOC analysts must be able to search Wazuh Indexer events from Ariba SOC using safe filters.

Required route:

```text
/hunting/live/
```

Required API:

```text
POST /hunting/api/search/
```

The browser must never connect directly to Wazuh Indexer.

Required flow:

```text
Browser
→ Django Hunting API
→ Validate filters and permissions
→ Wazuh Indexer
→ Sanitize result
→ Return paginated JSON
→ Render result table
```

## 1. Create the Django application

Run:

```bash
python manage.py startapp hunting
```

Create this structure:

```text
hunting/
├── __init__.py
├── apps.py
├── urls.py
├── views.py
├── forms.py
├── permissions.py
├── services/
│   ├── __init__.py
│   ├── query_builder.py
│   ├── query_validator.py
│   └── hunt_executor.py
├── templates/hunting/
│   ├── live_search.html
│   └── partials/
│       ├── _filter_form.html
│       ├── _result_table.html
│       └── _event_detail_modal.html
├── static/hunting/
│   ├── css/live_search.css
│   └── js/live_search.js
└── tests/
    ├── __init__.py
    ├── test_permissions.py
    ├── test_query_builder.py
    ├── test_views.py
    └── test_executor.py
```

Add `hunting` to `INSTALLED_APPS`.

Add to `config/urls.py`:

```python
path("hunting/", include("hunting.urls")),
```

## 2. Permissions

Add these permissions to the existing role-permission system:

```text
can_use_basic_hunting
can_use_advanced_hunting
```

Default permission matrix:

| Role    | Basic hunting | Advanced hunting |
| ------- | ------------: | ---------------: |
| L1      |           Yes |               No |
| L2      |           Yes |              Yes |
| L3      |           Yes |              Yes |
| SOC_ENG |           Yes |              Yes |
| SOC_MGR |           Yes |              Yes |
| ADMIN   |           Yes |              Yes |
| VIEWER  |            No |               No |
| MONITOR |            No |               No |

The `/hunting/live/` page and search API must enforce backend permission checks.

Inactive users or inactive analyst profiles must receive HTTP 403.

The API must return JSON HTTP 403, not an HTML redirect.

## 3. Live Search UI

Add a `Threat Hunting` menu to the existing navigation.

Only users with hunting permission should see it.

The Live Search page must contain:

* Search text
* Time range
* Agent
* Hostname
* Source IP
* Destination IP
* Username
* Rule ID
* Minimum rule level
* Severity
* MITRE tactic
* MITRE technique
* Event category/group
* Result limit
* Search button
* Reset button

Time-range options:

```text
Last 15 minutes
Last 1 hour
Last 6 hours
Last 24 hours
Last 7 days
Custom range
```

Default:

```text
Last 1 hour
Maximum 100 results per request
```

L1 restrictions:

```text
Maximum time range: 24 hours
Maximum result limit: 100
Basic approved filters only
```

L2/L3/Engineer/Manager/Admin:

```text
Maximum time range: 30 days
Maximum result limit: 500
Advanced filters allowed
```

## 4. Result table

Display:

```text
Timestamp
Rule level
Severity
Rule ID
Rule description
Agent ID
Agent name
Hostname
Source IP
Destination IP
Username
MITRE ID
MITRE tactic
MITRE technique
Decoder
Location
```

Each row must have a `View Event` action.

The event modal may show sanitized event JSON, but must redact:

```text
password
passwd
authorization
token
access_token
refresh_token
api_key
secret
cookie
session
private_key
credential
```

Never insert raw JSON using unsafe `innerHTML`.

Use safe text rendering.

## 5. Query builder

Create:

```text
hunting/services/query_builder.py
```

It must translate approved form filters into OpenSearch Query DSL.

Example output:

```json
{
  "size": 100,
  "sort": [
    {
      "timestamp": {
        "order": "desc"
      }
    }
  ],
  "query": {
    "bool": {
      "filter": [
        {
          "range": {
            "timestamp": {
              "gte": "now-1h",
              "lte": "now"
            }
          }
        },
        {
          "term": {
            "agent.id": "001"
          }
        }
      ],
      "must": [
        {
          "simple_query_string": {
            "query": "failed login",
            "fields": [
              "rule.description",
              "full_log",
              "data.*"
            ],
            "default_operator": "and"
          }
        }
      ]
    }
  }
}
```

Search only:

```text
wazuh-alerts-*
```

The index pattern must come from the approved server configuration, not from browser input.

## 6. Query security

Users must not be able to submit arbitrary JSON Query DSL in this phase.

Allow-list fields:

```text
timestamp
agent.id
agent.name
host.name
rule.id
rule.level
rule.description
rule.groups
rule.mitre.id
rule.mitre.tactic
rule.mitre.technique
source.ip
destination.ip
srcip
dstip
user.name
decoder.name
location
full_log
```

Allow-list operations:

```text
term
terms
range
match
simple_query_string
exists
```

Reject:

```text
script
script_score
runtime_mappings
percolate
regexp
wildcard on unrestricted fields
index override
stored scripts
update/delete operations
cluster operations
```

Validate:

* IP addresses
* Integer rule level
* Maximum result size
* Allowed time range
* Custom start/end time
* Maximum query-string length
* Allowed fields
* Allowed operators
* Role-specific limits

Invalid input returns HTTP 400 with a safe error message.

## 7. Indexer client

Use the existing Indexer client from:

```text
wazuh_integration/services.py
```

Refactor safely if necessary, but preserve the current alert synchronization.

Add a generic read-only method such as:

```python
def search(self, index_pattern, query_body):
    ...
```

Requirements:

* HTTPS in production
* TLS verification
* Explicit timeout
* No redirect following
* Maximum response-size protection
* Least-privilege read-only Indexer account
* No secrets in logs
* No query body containing credentials
* Return a controlled service exception
* Do not expose raw Indexer exception details to the browser

## 8. Hunt executor

Create:

```text
hunting/services/hunt_executor.py
```

Responsibilities:

```text
Receive validated filters
Build Query DSL
Call IndexerClient
Normalize search results
Redact sensitive fields
Return pagination metadata
Record audit event
```

Normalized API response:

```json
{
  "success": true,
  "data_source": "Wazuh Indexer",
  "took_ms": 31,
  "total": 148,
  "returned": 100,
  "time_range": {
    "from": "now-1h",
    "to": "now"
  },
  "next_cursor": null,
  "events": []
}
```

When the Indexer is unavailable:

```json
{
  "success": false,
  "status": "INDEXER_UNAVAILABLE",
  "message": "Threat hunting service is temporarily unavailable."
}
```

Return HTTP 503.

Do not return a valid-looking empty result when the Indexer request failed.

## 9. Pagination

Do not use unrestricted deep `from/size` pagination.

For the initial implementation use:

```text
sort by timestamp descending
secondary sort by _id
search_after cursor
```

The cursor must be server-generated and tamper-resistant.

Do not expose credentials or internal configuration in the cursor.

## 10. Audit logging

Record:

```text
User
Role
Search timestamp
Time range
Filters used
Result count
Execution duration
Success/failure
Source IP
Request ID
```

Do not record:

```text
Credentials
Tokens
Cookies
Complete sensitive raw events
```

Use the existing audit system where possible.

## 11. Performance

* Use Redis cache only for safe identical aggregation/filter metadata.
* Do not cache raw event results across users without including authorization scope.
* Add request timeout.
* Add per-user rate limiting.
* Prevent multiple Search button clicks while a request is running.
* Show loading state.
* Show Data Source and Last Updated.
* Display a clear Indexer unavailable message.

## 12. Tests

Mock all Wazuh Indexer calls.

Tests must never contact the real Indexer.

Add tests for:

* L1 can open basic hunting.
* L1 cannot request over 24 hours.
* L1 cannot request over 100 results.
* L2/L3 can use advanced limits.
* VIEWER and MONITOR receive 403.
* Inactive profile receives 403.
* Anonymous request is rejected.
* API returns JSON 403.
* Invalid IP returns 400.
* Invalid rule level returns 400.
* Invalid custom time range returns 400.
* Unapproved field/operator is rejected.
* Index override is impossible.
* Sensitive fields are redacted.
* Indexer failure returns 503, not empty success.
* Result pagination cursor works.
* Tampered cursor is rejected.
* Search creates an audit event.
* HTML/JavaScript safely renders malicious log content.
* No real network request occurs.

## 13. Completion checks

Run:

```bash
python manage.py makemigrations --check
python manage.py migrate
python manage.py check
python manage.py test hunting
python manage.py test
```

Do not ignore failures.

After implementation provide:

1. Changed files.
2. Migration details.
3. Final routes.
4. Role-permission matrix.
5. Example sanitized request and response.
6. Test results.
7. Remaining limitations.

Do not modify `.env`, production credentials, Docker ports, firewall rules, Wazuh users, real certificates, or live infrastructure.
