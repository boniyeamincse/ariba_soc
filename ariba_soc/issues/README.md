# Ariba SOC — Project Audit Issues

This directory contains a comprehensive audit of the Ariba SOC Django application, organized into 11 category folders. Each issue follows a structured template covering severity, priority, current problem, expected behavior, affected files, suggested fix, and QA verification.

## Issue Categories

| # | Category | Issues |
|---|----------|--------|
| 01 | [Function & Security](01-function-security/) | Hardcoded secrets, missing rate limiting, auth gaps |
| 02 | [UI/UX](02-ui-ux/) | Loading states, mobile nav, empty states |
| 03 | [Database](03-database/) | Indexing, cascades, model duplication |
| 04 | [Wazuh API](04-wazuh-api/) | Connection pooling, plaintext passwords, pagination |
| 05 | [RBAC](05-rbac/) | View-level checks, role enumeration mismatches |
| 06 | [Alert Workflow](06-alert-workflow/) | Reopen, bulk ops, SLA, escalation, notifications |
| 07 | [Reports](07-reports/) | CSV exports, openpyxl dependency, scheduling |
| 08 | [Performance](08-performance/) | N+1 queries, caching, query optimization |
| 09 | [Deployment](09-deployment/) | Docker, CI/CD, requirements, gunicorn |
| 10 | [Testing](10-testing/) | Unit/integration test coverage |
| 11 | [Documentation](11-documentation/) | README, API docs, deployment guide |

## Template

Each issue file includes:

- **Severity**: Critical / High / Medium / Low
- **Priority**: P0 (immediate) / P1 (this sprint) / P2 (next sprint) / P3 (backlog)
- **Current Problem**: What is broken or missing
- **Expected Behavior**: What should happen
- **Affected Files**: Exact file paths with line ranges
- **Suggested Fix**: Specific code-level remediation
- **QA Verification**: How to confirm the fix works
