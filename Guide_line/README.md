# 📚 Ariba SOC Documentation & Guidelines Hub

Welcome to the central documentation hub for **Ariba SOC** (Security Operations Center Platform).  
This directory is divided into two primary sections tailored for different roles:

---

## 🗂️ Documentation Sections

### 1. 👥 [User Guide (`user_guide/`)](file:///home/boni/Desktop/ariba_soc-main/Guide_line/user_guide/)
Tailored for **SOC Analysts (L1/L2/L3)**, **Incident Responders**, and **Security Managers**:
- **[01. Getting Started](file:///home/boni/Desktop/ariba_soc-main/Guide_line/user_guide/01_getting_started.md)**: Logging in, dashboard cockpit, navigation, roles & permissions.
- **[02. Alert Triage & Investigation](file:///home/boni/Desktop/ariba_soc-main/Guide_line/user_guide/02_alert_triage_and_investigation.md)**: Alert table, severity KPIs, deep-dive detail, IOC enrichment, MITRE ATT&CK.
- **[03. Kanban Board Workflow](file:///home/boni/Desktop/ariba_soc-main/Guide_line/user_guide/03_kanban_board_workflow.md)**: Visual alert triage, drag-and-drop workflow, status transitions, verdict assignments.
- **[04. Incident Management & SLAs](file:///home/boni/Desktop/ariba_soc-main/Guide_line/user_guide/04_incident_management.md)**: Escalating alerts into full security incidents, SLA monitoring, collaboration.
- **[05. Reporting & Data Export](file:///home/boni/Desktop/ariba_soc-main/Guide_line/user_guide/05_reporting_and_exports.md)**: Exporting CSVs, generating executive SOC PDF reports.

---

### 2. 💻 [Developer Guide (`developer_guide/`)](file:///home/boni/Desktop/ariba_soc-main/Guide_line/developer_guide/)
Tailored for **Core Developers**, **DevSecOps Engineers**, and **System Administrators**:
- **[01. System Architecture](file:///home/boni/Desktop/ariba_soc-main/Guide_line/developer_guide/01_system_architecture.md)**: Platform architecture, tech stack (Django, PostgreSQL, Redis, Wazuh Indexer/Manager).
- **[02. Local Development Setup](file:///home/boni/Desktop/ariba_soc-main/Guide_line/developer_guide/02_local_development_setup.md)**: Running the local Docker environment, migrations, running tests.
- **[03. Workflow & CI/CD Rules](file:///home/boni/Desktop/ariba_soc-main/Guide_line/developer_guide/03_workflow_and_cicd_rules.md)**: Mandatory strict 6-step pipeline (Test -> Commit -> Rebuild -> Docker Hub -> Remote).
- **[04. Wazuh Integration & Rule Authoring](file:///home/boni/Desktop/ariba_soc-main/Guide_line/developer_guide/04_wazuh_integration_and_rules.md)**: Alert synchronization, parsing/normalization, custom detection rule writing.
- **[05. Remote Deployment & Server Operations](file:///home/boni/Desktop/ariba_soc-main/Guide_line/developer_guide/05_remote_deployment_operations.md)**: Zero-source-code remote deployment, container lifecycle, backups & maintenance.
