# Code Review Findings — Ariba SOC

**Date**: 2025-09-05  
**Reviewer**: Automated review  
**Scope**: `/home/infosec/ariba_soc-main/ariba_soc/` (Django app + Docker setup)

---

## Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical / High | 7 |
| 🟡 Medium | 11 |
| 🟢 Low / Polish | 9 |
| 🐳 Docker / Infra | 4 |

---

## 🔴 Critical / High

### 1. Hardcoded PBKDF2 Salt in `EncryptedCharField`
**File**: `config/fields.py:29`  
**Risk**: If `DJANGO_CRYPTOGRAPHY_KEY` rotates, **all encrypted fields become undecryptable**. The salt `b'ariba-soc-field-encryption-v1'` is static — PBKDF2 output is deterministic for a given key.  
**Fix**: Store per-field salt (e.g., derive from field name + row PK) or use a random salt per encryption stored alongside ciphertext.

### 2. SSL Verification Disabled by Default
**Files**: `config/settings.py:152`, `infrastructure/.env:17`, `ariba_soc/.env:16`  
**Risk**: MITM on Wazuh Manager API (55000) and Indexer (9200). `WAZUH_VERIFY_SSL=False` ships as default.  
**Fix**: Default `True` in production; provision valid certs (Let's Encrypt or internal CA) and set `WAZUH_VERIFY_SSL=True` in prod `.env`.

### 3. Broad Exception Swallowing in Notifications
**File**: `alerts/services.py:126-127, 157-158`  
```python
except Exception as e:
    pass  # Silent failure
```  
**Risk**: Email/notification failures masked; escalations/assignments appear to succeed but recipients never notified.  
**Fix**: Log the error at minimum; consider a dead-letter queue or retry mechanism.

### 4. No Rate Limiting on Authentication
**File**: `accounts/views.py` (uses Django's built-in `LoginView`)  
**Risk**: Brute-force / credential stuffing on `/accounts/login/`.  
**Fix**: Add `django-axes` or `django-ratelimit`; lockout after N failed attempts.

### 5. `wazuh_alert_id` Unique Constraint Allows Nulls
**File**: `alerts/models.py:60, 144`  
```python
wazuh_alert_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
```  
**Risk**: Multiple alerts with `NULL` `wazuh_alert_id` can be inserted (PostgreSQL treats `NULL != NULL` for unique).  
**Fix**: Add partial unique index: `models.Index(fields=['wazuh_alert_id'], condition=~Q(wazuh_alert_id__isnull=True), unique=True)` or make field non-nullable after backfill.

### 6. `SECRET_KEY` Fallback in DEBUG Mode
**File**: `config/settings.py:13-14`  
```python
if DEBUG:
    SECRET_KEY = 'dev-secret-key-change-in-production'
```  
**Risk**: If `DEBUG=True` accidentally ships to prod, a known secret is used.  
**Fix**: Remove fallback; enforce `DJANGO_SECRET_KEY` env var always. Keep dev default only in `.env.example`.

### 7. Docker Compose Prod Uses External Image
**File**: `infrastructure/docker-compose.prod.yml:147`  
```yaml
image: boniyeamin/ariba_soc-web:latest
```  
**Risk**: No local build verification; image tag `latest` is mutable.  
**Fix**: Pin to semver tag (e.g., `v1.2.3`); document CI/CD pipeline that builds/pushes.

---

## 🟡 Medium

### 8. N+1 Query in `alert_table` View
**File**: `alerts/views.py:73`  
```python
assignees = Alert.objects.exclude(assignee__isnull=True).values_list('assignee_id', 'assignee__username').distinct()
```  
Runs on every page load.  
**Fix**: Cache for 60s or move to context processor.

### 9. `alert_board` Loads All Alerts Unpaginated
**File**: `alerts/views.py:93`  
```python
alerts = Alert.objects.select_related('assignee', 'source').all()
```  
**Risk**: OOM on large datasets (100k+ alerts).  
**Fix**: Add `Paginator` like `alert_table`.

### 10. `alerts_api` Returns Fixed 100 Records
**File**: `alerts/views.py:309-316`  
No pagination params (`limit`, `offset`).  
**Fix**: Support `?limit=50&offset=0` with max cap (e.g., 500).

### 11. `update_alert` Function Too Large (85 lines)
**File**: `alerts/services.py:26-110`  
Mixes: field updates, audit logging, notifications, comments, escalation, remediation, closure, lessons learned.  
**Fix**: Split into `update_alert_fields()`, `log_audit()`, `notify_assignment()`, `handle_escalation()`, `handle_closure()`, etc.

### 12. `assign_alert` Notification Logic Confusing
**File**: `alerts/services.py:166-168`  
```python
notify = alert.assignee != assignee and assignee != user
```  
**Fix**: Extract to `_should_notify_assignment(old_assignee, new_assignee, actor)` with docstring.

### 13. No Database Connection Pooling
**File**: `config/settings.py:92-101`  
**Fix**: Add `CONN_MAX_AGE = 60` (or higher) to `DATABASES['default']`.

### 14. `alert_bulk_action` Loses Per-Alert History
**File**: `alerts/views.py:348`  
```python
old_val = ', '.join(alerts.values_list('status', flat=True).distinct())
```  
Single audit log entry for all alerts; can't trace which alert had which old status.  
**Fix**: Loop and `create_audit_log()` per alert.

### 15. `dashboard_stats_api` Runs 7 Separate Count Queries
**File**: `dashboard/views.py:46-53`  
**Fix**: Combine with conditional aggregation:
```python
Alert.objects.aggregate(
    critical=Count('id', filter=Q(severity='Critical')),
    high=Count('id', filter=Q(severity='High')),
    ...
)
```

### 16. PDF Export Has Hardcoded Branding
**File**: `reports/views.py:286`  
```python
filename="AkijGroup_SOC_Report_..."
```  
**Fix**: Read from `SystemSetting` (e.g., `COMPANY_NAME`, `TEAM_NAME`).

### 17. `SECURE_PROXY_SSL_HEADER` Missing
**File**: `config/settings.py:169` (commented)  
**Risk**: When nginx terminates TLS, `request.is_secure()` returns `False`, breaking `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`.  
**Fix**: Uncomment and set:
```python
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

### 18. Requirements Not Pinned
**File**: `requirements.txt`  
```txt
Django>=5.1,<5.2
```  
**Fix**: Pin exact versions (`Django==5.1.7`) for reproducible builds; use `pip-tools` or `uv` to manage.

---

## 🟢 Low / Polish

### 19. Add Type Hints Throughout
Django 5.1 supports `from __future__ import annotations`; add hints to views, services, models.

### 20. `monitor/services.py` Not Reviewed
Globe arcs, live ops logic unseen — review separately.

### 21. Tests Are Minimal
**Files**: `*/tests.py` — mostly empty stubs.  
**Fix**: Add `pytest`, `factory_boy`, `pytest-django`; target >80% coverage on services/views.

### 22. `alert_move_api` Returns 400 for Invalid Status but No Detail
**File**: `alerts/views.py:404`  
**Fix**: Return `{'success': False, 'error': 'Invalid status: {new_status}'}`.

### 23. `wazuh_sync` Management Command Hardcodes Time Range
**File**: `wazuh_integration/management/commands/wazuh_sync.py:8`  
Default `--time-range 1h`; scheduler uses `10m`.  
**Fix**: Align defaults; document expected overlap.

### 24. `EnrichmentService` Swallows All Exceptions
**File**: `wazuh_integration/enrichment_service.py:48-49, 74-75`  
`except Exception as e: logger.error(...)` — no retry, no alerting.  
**Fix**: Add retry with backoff; emit metric on failure.

### 25. `IndexerClient` Auth Uses Basic Auth in Session
**File**: `wazuh_integration/services.py:101`  
```python
self.session.auth = (self.username, self.password)
```  
Sent on every request (including `_cluster/health`).  
**Fix**: Use token-based auth like `ManagerClient` if Indexer supports it; else document why basic auth is acceptable.

### 26. `normalize_es_alert` Duplicates Logic from `normalize_alert`
**File**: `wazuh_integration/services.py:209-262` vs `156-206`  
**Fix**: Extract common field mapping to shared helper.

### 27. Cluster Config Disabled but Present
**File**: `infrastructure/config/wazuh_cluster/wazuh_manager.conf:297`  
```xml
<disabled>yes</disabled>
```  
**Fix**: Remove cluster section if not used, or document multi-node setup steps.

---

## 🐳 Docker / Infrastructure

### 28. No Log Rotation for Containers
**File**: `infrastructure/docker-compose.yml`  
**Fix**: Add logging driver:
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "5"
```

### 29. Wazuh Indexer JVM Heap Fixed at 1GB
**File**: `infrastructure/docker-compose.yml:60`  
```yaml
- "OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g"
```  
**Risk**: OOM on small hosts; underutilized on large.  
**Fix**: Make configurable via env (`WAZUH_INDEXER_HEAP`).

### 30. `nginx.docker.conf` Not Reviewed
**File**: `ariba_soc/deploy/nginx.docker.conf`  
**Check**: Proxy headers (`X-Forwarded-Proto`, `X-Forwarded-For`), buffering, rate limiting, timeouts.

### 31. No Healthcheck for Wazuh Manager/Indexer in Prod Compose
**File**: `infrastructure/docker-compose.prod.yml`  
Only `db`, `redis`, `web` have healthchecks.  
**Fix**: Add healthchecks for `wazuh.manager` (curl 55000) and `wazuh.indexer` (curl 9200/_cluster/health).

---

## Suggested Fix Order

| Priority | Issues |
|----------|--------|
| **P0 (Do First)** | 1, 2, 3, 4, 5 |
| **P1 (This Sprint)** | 6, 7, 8, 9, 10, 11, 12, 13 |
| **P2 (Next Sprint)** | 14, 15, 16, 17, 18, 22, 23 |
| **P3 (Backlog)** | 19, 20, 21, 24, 25, 26, 27, 28, 29, 30, 31 |

---

## Related Files to Update

- `config/fields.py` — salt handling
- `config/settings.py` — SSL verify, proxy header, conn max age
- `alerts/models.py` — partial unique index
- `alerts/views.py` — pagination, bulk action audit
- `alerts/services.py` — split `update_alert`, notification logic
- `dashboard/views.py` — aggregated queries
- `reports/views.py` — configurable branding
- `wazuh_integration/services.py` — auth, normalize dedup, enrichment retries
- `infrastructure/docker-compose.yml` — logging, healthchecks, heap env
- `requirements.txt` — pin versions
- `ariba_soc/deploy/nginx.docker.conf` — proxy headers, rate limits

---

## Verification Checklist

After fixes, verify:
- [ ] `WAZUH_VERIFY_SSL=True` works with valid certs
- [ ] `DJANGO_CRYPTOGRAPHY_KEY` rotation procedure documented & tested
- [ ] Login rate limiting blocks after 5 failures
- [ ] `alert_board` paginates at 50/page
- [ ] `alerts_api` respects `limit`/`offset`
- [ ] Bulk action creates per-alert audit logs
- [ ] Dashboard stats API uses single query
- [ ] PDF export uses `SystemSetting` for company name
- [ ] `SECURE_PROXY_SSL_HEADER` works behind nginx TLS
- [ ] Docker containers rotate logs
- [ ] All tests pass (`pytest`)
- [ ] Security headers present (HSTS, CSP, etc.)

---

*Generated from automated code review. Review manually before acting.*