# Ariba SOC — Full Code Review & Findings
**Date:** 2026-10-12
**Target:** `http://localhost:8080/` (local Docker stack) + full source of `ariba_soc/` (Django 5.1)
**Method:** 4 parallel deep code reviews (alerts/dashboard · accounts/settings/audit · incidents/vulnerabilities/hunting · reports/monitor/wazuh/config) + live runtime verification
**Verdict:** **NO-GO for production.** The alert workflow engine is entirely broken at runtime (HTTP 500 on every transition), RBAC is broadly unenforced, and several secrets/exports are exposed. This review is code-focused; the earlier deployment review (2026-10-11, target 10.24.66.2) is cross-referenced at the end.

---

## 1. Live-Verified Runtime Findings (verified today with curl / container logs)

| # | Sev | Finding | Evidence |
|---|-----|---------|----------|
| L-1 | **Critical** | **Every alert workflow action (claim/escalate/close/reopen) returns HTTP 500.** `select_for_update()` is called outside any transaction (`ATOMIC_REQUESTS` is off). The entire triage workflow is dead. | `POST /647/claim/` → 500; container log: `django.db.transaction.TransactionManagementError: select_for_update cannot be used outside of a transaction` at `alerts/workflow.py:518`, caller `:189` |
| L-2 | **Critical** | **Media tree (SOC report PDFs, avatars) served unauthenticated by nginx.** Anyone can download confidential generated reports without login. | `GET /media/avatars/boniyeamin.jpeg` → **200** with no cookies; nginx `location /media/` has no auth; reports exist at `/app/media/reports/*.pdf` |
| L-3 | Info | Stack is up: 8/8 containers healthy; login works (`admin`); dashboard/alerts/incidents/vulnerabilities/reports/audit/wazuh pages all 200 after login. | `docker ps`, login flow 302→200 |

---

## 2. Critical Findings (code)

### CR-1 — Alert workflow engine fundamentally broken (`alerts/workflow.py`)
- **CR-1a: All transitions 500 in production** — `_acquire_lock()` (`workflow.py:516-518`) runs `select_for_update()` **before** entering `transaction.atomic()`, and `ATOMIC_REQUESTS` is not enabled (`config/settings.py`). On PostgreSQL every claim/escalate/accept/return/resolve/close/reopen/incident action raises `TransactionManagementError` (live-verified, L-1). Tests pass only because SQLite silently no-ops the lock.
- **CR-1b: New alerts can never leave `NEW`** — alerts are ingested with default `workflow_state='NEW'`, but `ALLOWED_TRANSITIONS['NEW'] = {'QUEUED_L1'}` only (`workflow.py:18`) while `claim` validates toward `IN_PROGRESS_L1` (`:193`). The L1 queue (`workflow_state='QUEUED_L1'`) is permanently empty; `NEW` is also missing from dashboard `OPEN_WORKFLOW_STATES` (`dashboard/views.py:13`), so fresh alerts are excluded from SLA/risk widgets.
- **Fix:** wrap lock+validation+mutation in one `transaction.atomic()`; default new open alerts to `QUEUED_L1` (or allow `NEW→IN_PROGRESS_L1`).

### CR-2 — Generated SOC reports & media publicly downloadable (`deploy/nginx.docker.conf:13-15`)
`location /media/ { alias /app/media/; }` serves the whole media tree with no auth; `reports/services.py` writes every generated report (PDF/CSV/XLSX) into `MEDIA_ROOT/reports/` with predictable timestamped names. Live-verified (L-2). **Fix:** serve reports via an authenticated Django view or `location /media/reports/ { deny all; }` + authenticated download endpoint; move reports out of web-served media.

### CR-3 — Privilege escalation: non-admins can mint ADMIN users (`settings_manager/views.py:31-38`, `forms.py:13`, `views.py:193-205,240-251`)
Settings access is granted to `SOC_MGR`/`SOC_ENG`/`ADMIN`, but the user forms offer `role=ADMIN` with no restriction, no self-edit guard — a SOC_ENG can create an ADMIN, promote themselves, or bulk-promote. Prior report C-08 is only **partially fixed** (L1/VIEWER now blocked; SOC_ENG/SOC_MGR still escalate).

### CR-4 — Settings allowlist is DB-writable = persistent backdoor (`settings_manager/views.py:24-28,900-915`)
`_get_allowed_roles()` reads `SystemSetting.get_setting('settings_allowed_roles')`, and the `system_settings` view accepts arbitrary key/value writes. A SOC_ENG can POST `key=settings_allowed_roles, value=L1,L2,VIEWER,MONITOR` and grant every role full settings/user-management access permanently.

### CR-5 — Incident permissions never seeded on fresh installs → "Create Incident" 403 for **everyone incl. ADMIN** (`accounts/migrations/0010_add_incident_permissions.py`)
`0010` adds the six incident permission flags with `default=False` **after** the seed migrations (`0003`/`0006`) ran; no `RunPython` seeds them. All roles end with `can_create_incident=False` etc. until an admin hand-edits the matrix. Tests mask this by granting perms in `setUp`.

---

## 3. High Findings

### Application security / RBAC
- **H-1 Missing authorization across core views** (`alerts/views.py`): `alert_edit` (`:184`), `alert_add_comment` (`:220`), and all asset views (`:549-600`) are `@login_required` only — VIEWERs/deactivated users can reassign any alert, change priority, comment, and create/edit/delete assets.
- **H-2 RBAC bypass via TIER_ACTIONS** (`alerts/workflow.py:41` vs `views.py:448`): `alert_close` consults only role tiers, never `can_close_alert`; an L1 refused bulk-close can close the same alert via the single close endpoint. `can_assign_others` similarly unenforced on `alert_edit`.
- **H-3 Permission matrix largely decorative** (`accounts/models.py:60-62`): 9 toggles (`can_manage_users`, `can_view_audit_logs`, `can_manage_wazuh`, `can_view_reports`, `can_export_reports`, `can_escalate_alert`, `can_reassign`, `can_add_remediation`, `can_mark_incident`) have **zero enforcement call sites**.
- **H-4 Deactivated accounts can still log in** (`settings_manager/forms.py:40,79`): forms set only `profile.is_active`, never `user.is_active`; `_check_settings_access` has no active check at all.
- **H-5 Incident assign/close/reopen has no permission gate** (`incidents/views/assignment.py:9`, `transition.py:15`): only MONITOR is blocked; `INCIDENT_PERMISSIONS` dict is dead code — L1/VIEWER can close incidents.
- **H-6 Vulnerability remediation has no granularity** (`vulnerabilities/views.py:104-174`): L1 can risk-accept critical CVEs, mark false positives, resolve; `vulnerability_permission_required` decorator exists but is never used.
- **H-7 Audit middleware is a no-op** (`audit/middleware.py:3-9`): `AuditLog` never written; LOGIN/LOGOUT/USER_CREATED audit actions are dead — compliance gap. (Prior report H-07, unfixed.)
- **H-8 Password resets bypass all validators** (`settings_manager/forms.py:315-323`): `validate_password()` never called; `AUTH_PASSWORD_VALIDATORS` skipped for admin-set passwords on any account.
- **H-9 No rate limiting/lockout on login** (`accounts/urls.py:20`): no django-axes/ratelimit anywhere; brute-force/stuffing unmitigated. (Prior H-04, unfixed.)
- **H-10 Audit log viewer is login-only** (`audit/views.py:7-12`): any authenticated account (incl. MONITOR wallboard) can read every audit row incl. IPs and old/new values; `can_view_audit_logs` ignored.
- **H-11 Lower-privileged settings users can delete/deactivate/demote ADMIN accounts** (`settings_manager/views.py:139,187,264`): protection keys on `is_superuser` only, but form-created ADMINs aren't superusers.
- **H-12 Permission matrix rewriteable by any settings user** (`settings_manager/views.py:348-356`): SOC_ENG can grant own role every capability or strip ADMIN's.

### Broken core functionality
- **H-13 Detail-page Close/Escalate always 409** (`templates/ariba_soc/alert_detail.html:528-566`): workflow forms omit hidden `workflow_version` → defaults to 1 → stale-version rejection after any transition. Non-numeric version → unhandled 500.
- **H-14 L3 escalation can never be accepted** (`alerts/workflow.py:284`): validation hardcodes `IN_PROGRESS_L2` instead of the target tier; L3 escalations stuck in `PENDING_L3_ACCEPTANCE` forever.
- **H-15 Workflow never updates `alert.status`** (`alerts/workflow.py:427-434`): board (status-driven) and dashboards (workflow_state-driven) permanently disagree; `_derive_legacy_status()`/`_set_workflow_state()` are dead code. Reverse desync too: `alert_move_api`/bulk actions write `status` bypassing the state machine and optimistic locking.
- **H-16 Incident status buttons all dead** (`incidents/templates/incidents/incident_detail.html:117` vs `views/transition.py:29-44`): template POSTs lowercased **status names** (`confirmed`, `investigating`, `containment`…) while server `fn_map` keys are **verbs** (`confirm`, `investigate`, `contain`…) — intersection is empty; every transition returns `Unknown action`. Evidence textarea conditions also never match (`t == 'CONTAIN'` vs real `CONTAINMENT`).
- **H-17 `Asset.save()` crashes for MEDIUM assets** (`alerts/models.py:152-156`): short-circuit `or` prevents `kwargs.pop('recalc_multiplier')` when multiplier==1.0 → `TypeError` → HTTP 500 editing any medium asset.
- **H-18 PDF report generation always fails** (`reports/services.py:239,839-842,910` + `requirements.txt:11`): guard checks dead `HAS_REPORTLAB` instead of `pisa is None`; when xhtml2pdf import fails, `pisa.CreatePDF` → `AttributeError` (matches scheduler error). `xhtml2pdf>=0.2` unpinned. Reportlab path (`_write_pdf`) is dead code.
- **H-19 Owner-assignment dropdowns permanently empty** (`incidents/views/detail.py:21-29`, `vulnerabilities/views.py:56-64`): `users` never passed to context → `<select>` renders placeholder only; assignment impossible from UI in both apps.
- **H-20 Alert sync dedup broken for id-less docs; created counts lie** (`wazuh_integration/services.py:376-389,459`): dedup pre-check misses docs without `id`; positional fallbacks (`"0"`,`"1"`) collide on the unique constraint and are silently dropped via `ignore_conflicts=True` while `created_count = len(batch)` overstates. Scheduler (5-min) and manual sync can race.

### Data exposure / injection
- **H-21 Stored/DOM XSS in executive dashboard** (`templates/ariba_soc/dashboard_home.html:254,263`): attacker-influenceable `alert_name`/`hostname` interpolated into `innerHTML` unescaped → JS execution in any viewer's session.
- **H-22 CSV/Excel formula injection in exports** (`reports/views.py:147-168`): `alert_name`/`hostname`/`username` from telemetry written raw; `=cmd|...` formulas execute in Excel when analyst opens export.
- **H-23 IOC provider API keys rendered in plaintext** (`settings_manager/forms.py:325-337`): decrypted `api_key` shown in `TextInput` value attribute; also passed as URL query string (`?token=...`) → leaks to logs/Referers. Blank submit wipes stored secrets.
- **H-24 `javascript:` URLs in vulnerability references** (`vulnerabilities/templates/vulnerabilities/detail.html:41,43`): reference URLs from indexer rendered as `href` with no scheme allowlist → click XSS.
- **H-25 Reports/exports lack authorization** (`reports/views.py:126-156`): `export_csv`/`export_excel`/`generate_now` are login-only — MONITOR/VIEWER can dump full alert tables and trigger report emails.
- **H-26 `/accounts/users/` exposes full analyst roster to any authenticated user** (`accounts/views.py:52-55`; MONITOR allowlist includes `/accounts/`).

### Config / infra (app-side)
- **H-27 `DEBUG`/`ALLOWED_HOSTS` default insecure** (`config/settings.py:8,24`): default `True`/`'*'` if env omitted; `.env.example` ships the insecure template. (Prior C-03/C-04 unfixed.)
- **H-28 Wazuh TLS verify defaults False in env AND models** (`config/settings.py:155`, `wazuh_integration/models.py:26,45`). (Prior C-05/H-13 unfixed.)
- **H-29 Email backend hardcoded to console** (`config/settings.py:180`): all SMTP env vars dead; `fail_silently=True` (`reports/services.py:212`) hides even errors — report emails silently never sent. (Prior H-11 unfixed.)
- **H-30 Gunicorn `forwarded_allow_ips = '*'`** (`gunicorn.conf.py:12`): anyone can spoof `X-Forwarded-For`/`Proto`, defeating IP audit trails and future lockouts.
- **H-31 Notification failures silently swallowed** (`alerts/services.py:125-157,187-188`): bare `except: pass` around assignment/escalation notifications and alarms. (Prior H-06 partly unfixed.)
- **H-32 Open redirect + unvalidated Active Response command** (`wazuh_integration/views.py:209,214,310-311`): `next` redirected without host validation; `command` not validated against allowlist before being sent to Wazuh AR endpoint. Same `next` open-redirect pattern at `settings_manager/views.py:1216-1218`.
- **H-33 Unbounded indexer fetch (5000 cap, no pagination)** (`wazuh_integration/services.py:213`): detections beyond newest 5000 silently lost; report analytics load full tables into memory (`reports/services.py:324,653`) — OOM DoS via `?range=all`.

---

## 4. Medium Findings (condensed)

| ID | Area | Finding | Location |
|----|------|---------|----------|
| M-1 | alerts | Transition audit logs record `from_state` **after** mutation → `CLOSED→CLOSED`, audit trail useless | `workflow.py:264,412,441,476-479,504` |
| M-2 | alerts | Bulk assign no-ops but reports success (two selects share `name="value"`); bulk close bypasses closure rules/state machine | `alert_table.html:30-36`, `views.py:408-456` |
| M-3 | alerts | `status_updated_at` is `auto_now_add` but used as "last change" in metrics → `fp_rate`/`closed_today`/SLA stats skewed | `models.py:241`, `dashboard/views.py:103,252,332` |
| M-4 | alerts | `alert_move_api` lacks `@require_POST`/JSON guard → 500 on GET; bypasses workflow | `views.py:468-472` |
| M-5 | alerts | IR/IT & Management escalate buttons dead (`tier=irit/management` rejected by workflow) | `alert_detail.html:536-544`, `workflow.py:218` |
| M-6 | settings | All `*_toggle` settings handlers skip `_log_setting_change` — silent audit-log tampering | `settings_manager/views.py:481-489,890-898` |
| M-7 | settings | IOC key in URL query string; blank-field saves wipe encrypted secrets | `views.py:1362`, forms as H-23 |
| M-8 | incidents | Incident number generation racy (string `Max` aggregate, no retry) + naive `datetime.now()` year | `incidents/models.py:79-94` |
| M-9 | vulns | `accept_risk`/`mark_false_positive` bypass `ALLOWED_TRANSITIONS` state machine; audit `old_value` recorded after mutation (= new value) | `services/remediation.py:14-103` |
| M-10 | vulns | Sync overwrites analyst-set `priority` on every sync; `due_at` not recalculated | `services/normalizer.py` |
| M-11 | hunting | Hunt search 500s when indexer returns integer `hits.total` (guard written after crash) and when `rule.mitre` is null | `hunt_executor.py:47-49,96` |
| M-12 | hunting | L1 24h hunt limit not enforced (`7d`/unbounded `custom` pass); L1 field filters silently **discarded** → unfiltered data shown as filtered | `query_validator.py:81-86`, `query_builder.py:80-82` |
| M-13 | hunting | Hunt audit IP always empty; failed hunts unaudited; inconsistent log redaction (`full_log` unredacted) | `hunt_executor.py:37,63,154-159` |
| M-14 | vulns/incidents | Unvalidated `page`/`owner` params → `ValueError` 500; empty owner selection crashes assign | `vulnerabilities/views.py:28,73-76`, `assignment.py:19,35` |
| M-15 | vulns | Vulnerability `inventory`/`assets`/`cves` unreachable from UI (dead-end nav); pagination drops filters | `urls.py`, `overview.html`, `inventory.html:68` |
| M-16 | reports | `wazuh_health` behind login leaks internal API URL; broken as LB healthcheck | `wazuh_integration/views.py:187-201` |
| M-17 | monitor | Attack-globe geolocation over plaintext HTTP (`http://ip-api.com`) — forgeable intel + IP leakage | `monitor/services.py:227` |
| M-18 | accounts | GET-based logout → forced-logout CSRF | `accounts/urls.py:8-14` |
| M-19 | alerts | Date filter `alert_time__lte` drops final day; `alert_board` runs 11 unsliced querysets; `recalculate_all_alerts_risk` loops full table in-request | `views.py:79-82,140-151,623-629` |

**Low (notable):** superuser without profile 500s on Wazuh views (`wazuh_integration/views.py:21-44`); `ManagerClient._request` returns `None` after 401 exhaustion (`services.py:57-68`); IPInfo key in URL query (`enrichment_service.py:33`); open redirect via `HTTP_REFERER` (`alerts/views.py:217`); dead routes (`hunting:event_detail` hardcoded 404).

---

## 5. Cross-Check vs Deployment Report (2026-10-11, host 10.24.66.2)

| Prior finding | Status in code today |
|---|---|
| C-03/C-04 DEBUG=True, ALLOWED_HOSTS=* | **Unfixed** (H-27) |
| C-05/H-13 TLS verify False | **Unfixed** (H-28) |
| C-08 Privilege escalation via user mgmt | **Partially fixed** — L1/VIEWER blocked; SOC_ENG/SOC_MGR still escalate (CR-3) |
| H-03 Missing authorization on endpoints | **Unfixed / expanded** (H-1…H-6, H-25, H-26) |
| H-04 No login rate limiting | **Unfixed** (H-9) |
| H-05 API keys in cleartext forms | **Unfixed** (H-23) |
| H-06 Notifications swallowed | **Unfixed** (H-31) |
| H-07 Audit middleware no-op | **Unfixed** (H-7) |
| H-11 Email console backend | **Unfixed** (H-29) |
| C-10 Plain HTTP / no secure cookies | **Unfixed** (local; nginx still HTTP-only) |

New in this review (not in the deployment report): the entire workflow engine being broken (CR-1/L-1), unauthenticated media/report downloads (CR-2/L-2), incident permissions unseeded (CR-5), all incident transition buttons dead (H-16), L3 accept impossible (H-14), XSS in dashboard (H-21), CSV injection (H-22), and the settings allowlist backdoor (CR-4).

---

## 6. Top Priority Fix Order

1. **CR-1 / L-1** — Wrap `workflow._acquire_lock` + mutations in `transaction.atomic()`; add `NEW→QUEUED_L1` at ingestion. (Nothing else matters until triage works.)
2. **CR-2 / L-2** — Lock down `/media/reports/` (nginx deny + authenticated download view).
3. **H-16** — Align incident transition verbs (template vs `fn_map`); add a view-level transition test.
4. **CR-3 / CR-4 / H-4 / H-8** — Harden settings: admin-only role assignment, self-edit guard, hard-coded allowlist, `user.is_active` sync, `validate_password`.
5. **H-13 / H-14 / H-15 / H-17** — Add `workflow_version` to detail forms, fix L3 validation target, sync `status`↔`workflow_state`, fix `Asset.save` kwarg pop.
6. **H-1…H-6, H-10, H-25, H-26** — Enforce the permission matrix everywhere (wire the 9 dead toggles; gate exports, audit, user list, edit/comment/asset views).
7. **H-21 / H-22 / H-24** — Escape dashboard `innerHTML`, sanitize CSV cells, scheme-allowlist reference URLs.
8. **H-18 / H-29** — Fix PDF guard (`if pisa is None`), pin `xhtml2pdf`, env-drive `EMAIL_BACKEND`, drop `fail_silently`.
9. **H-27 / H-28 / H-30 + prior C-03/C-05/C-09/C-10** — Production config hardening (DEBUG/HOSTS defaults, TLS verify, gunicorn proxy IPs, secrets perms) per the deployment report.
10. **H-9 / M-11…M-13** — Login lockout (django-axes); hunting 500 guards & L1 time-range enforcement.

---

## 7. What's Clean (verified)
- CSRF: middleware on, all mutating forms carry `{% csrf_token %}`, no `csrf_exempt`.
- Login `next=` open redirect **not** present on the auth view (stock `LoginView` validation).
- Session fixation: stock `login()` key cycling.
- `ProfileForm` mass assignment: `role` not in `fields`.
- No `|safe`/`mark_safe` in the reviewed apps' templates (except the JS `innerHTML` sink, H-21).
- SSRF in monitor geolocation: private-IP filter correctly applied (only the HTTP scheme is the issue).

---
*Generated by automated multi-agent code review + manual runtime verification. All findings quote verified source locations; line numbers refer to the working tree at review time.*
