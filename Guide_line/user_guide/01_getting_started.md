# 👥 User Guide: 01. Getting Started with Ariba SOC

## 1. Introduction
**Ariba SOC** is a security operations platform integrating Wazuh OpenSearch/Indexer event telemetry into a unified investigation and incident response cockpit.

---

## 2. Logging In
1. Open your web browser and navigate to the Ariba SOC web portal:
   - **Local Development:** `http://localhost:8080/`
   - **Remote Server:** `http://<SERVER_IP>/` (or your configured HTTPS domain)
2. Enter your credentials on the login page:
   - **Username:** Your analyst username
   - **Password:** Your assigned password
3. If MFA is enabled for your profile, provide the OTP code.

---

## 3. Top Navigation & Main Modules
Once logged in, the topbar and sidebar provide access to all SOC operations:
- **Alert Table (`/`):** The primary tabular view of all ingested alerts with real-time severity KPI cards and bulk operations.
- **Alert Board (`/board/`):** A Kanban view organized by triage stage (New, In Progress, Escalated, Closed, etc.).
- **Incident Response (`/incidents/`):** Active security incidents, war-rooms, response steps, and timelines.
- **Asset Directory (`/alerts/assets/`):** Inventory of all monitored endpoints with risk multipliers.
- **Vulnerabilities (`/vulnerabilities/`):** CVE scanning results, affected packages, and severity filters.
- **Reports (`/reports/`):** SOC shift summaries, executive PDF reports, and compliance exports.
- **Settings (`/settings/`):** Management of SOC teams, alarm triggers, SLA policies, and user profiles (accessible based on role permissions).

---

## 4. Analyst Roles & Tiers
Ariba SOC implements Role-Based Access Control (RBAC):
- **L1 Analyst (Triage):** Ingests new alerts, verifies false positives, acknowledges alerts, and escalates true anomalies.
- **L2 Analyst (Senior / Responder):** Deep-dive root-cause analysis, memory/network log investigation, creating incidents.
- **L3 / Threat Hunter:** Proactive threat hunting, rule creation, malware signature analysis.
- **SOC Manager / Admin:** Team management, SLA assignment, system configurations, and executive reporting.
