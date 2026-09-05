# Ariba SOC Audit Issues

Security, performance, and code quality audit of the Ariba SOC Django application.

## Summary

| Severity | Count | Priority |
|----------|-------|----------|
| **Critical** | 3 | P0 |
| **High** | 7 | P1 |
| **Medium** | 10 | P2 |
| **Low** | 8 | P3 |
| **Total** | **28** | |

## Categories

| Category | Issues |
|----------|--------|
| Security | 15 |
| Performance | 7 |
| Code Quality | 5 |
| Missing Features | 3 |

## Issue Files

```
docs/issues/
├── 01-critical/
│   ├── SEC-001-credentials-in-repo.md
│   ├── SEC-002-missing-login-required-settings.md
│   └── PERF-001-bulk-actions-no-transaction.md
├── 02-high/
│   ├── SEC-003-no-rate-limiting-login.md
│   ├── SEC-004-no-rate-limiting-api.md
│   ├── SEC-005-no-password-validation.md
│   ├── SEC-006-silent-notification-failures.md
│   ├── SEC-007-missing-csp-header.md
│   ├── PERF-002-dashboard-stats-no-cache.md
│   └── PERF-003-context-processor-queries.md
├── 03-medium/
│   ├── SEC-008-session-timeout-too-long.md
│   ├── SEC-009-allowed-hosts-wildcard.md
│   ├── SEC-010-redis-no-auth.md
│   ├── SEC-011-http-external-api.md
│   ├── SEC-012-no-2fa.md
│   ├── SEC-013-no-api-tokens.md
│   ├── PERF-004-role-permission-no-cache.md
│   ├── PERF-005-alert-board-n-plus-1.md
│   ├── PERF-006-reports-count-queries.md
│   ├── CODE-001-audit-middleware-noop.md
│   ├── CODE-002-settings-dry-violation.md
│   └── CODE-003-scripts-force-sqlite.md
├── 04-low/
│   ├── CODE-004-user-list-pii-leak.md
│   ├── CODE-005-tasks-print-instead-of-logging.md
│   ├── CODE-006-model-str-none-user.md
│   ├── CODE-007-gunicorn-log-directory.md
│   ├── PERF-007-wallboard-len-vs-count.md
│   ├── SEC-014-no-sla-breach-notifications.md
│   ├── SEC-015-no-playbook-support.md
│   └── SEC-016-no-websocket-alerts.md
└── README.md
```

## Top Priority Fixes

1. Add `@login_required` to ALL settings_manager views (SEC-002)
2. Add rate limiting to login and API endpoints (SEC-003, SEC-004)
3. Add password validation to admin reset (SEC-005)
4. Log notification failures (SEC-006)
5. Add CSP header (SEC-007)
6. Cache dashboard stats queries (PERF-002)
7. Wrap bulk actions in `transaction.atomic()` (PERF-001)
8. Set session timeout to 1 hour (SEC-008)

## How to Use

Each issue file contains:
- **Severity**: Critical / High / Medium / Low
- **Priority**: P0 / P1 / P2 / P3
- **Category**: Security / Performance / Code Quality
- **Current Problem**: What is broken
- **Expected Behavior**: What should happen
- **Affected Files**: Exact file paths
- **Suggested Fix**: Code-level remediation
- **QA Verification**: How to confirm the fix
