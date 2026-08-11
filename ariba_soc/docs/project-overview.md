# Project Overview

## Vision

Ariba SOC aims to be a lightweight, modern, and extensible SIEM web application that bridges the gap between raw security event data (from Wazuh) and actionable intelligence for SOC analysts. It provides an intuitive interface for triage, escalation, reporting, and compliance without the overhead of enterprise-grade SIEMs.

## Target Users

| Role | Description |
|------|-------------|
| **L1 Analyst** | First line of defense — triages incoming alerts, acknowledges, escalates |
| **L2 Analyst** | Deep investigation — handles escalated alerts, sets dispositions |
| **SOC Manager** | Oversees team performance, generates reports, configures SLAs |
| **Administrator** | Full system control — users, settings, integrations, audit logs |

## Key Design Goals

1. **Dual Wazuh Connectivity** — Connect to both the Wazuh Manager (REST API, JWT auth) and the Wazuh Indexer (OpenSearch API, Basic Auth) for maximum flexibility.
2. **Role-First Security** — Every view, API, and action is gated by `@login_required`, `@role_required`, and template-level permission checks.
3. **Audit Everything** — Every alert status change, assignment, and configuration update is stored in `AuditLog` or `AlertAuditLog`.
4. **Glassmorphism UI** — A visually premium frontend that is pleasant to use during long shifts.
5. **Zero Vendor Lock-in** — Wazuh integration is modular; swapping the backend SIEM is a service-layer change.

## Scope

- **In scope:** Alert ingestion from Wazuh, kanban board triage, RBAC, notifications, reporting, audit, settings management.
- **Out of scope:** Real-time streaming (polling-based), custom SIEM rules, machine learning detection, multi-tenancy.

## Current Status

Production-ready integration with a live Wazuh 4.x server (`10.24.66.2`). Both Manager API and Indexer API connections verified. 600+ alerts synced with dedup. All 19 tests passing. Deployed behind Nginx + Gunicorn on port 8091.
