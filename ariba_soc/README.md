# 🛡️ Ariba SOC 

Ariba SOC is a premium, modern Security Information and Event Management (SIEM) dashboard tailored for Security Operations Centers. Built to seamlessly integrate with **Wazuh**, it provides real-time alert triage, automated escalations, role-based access controls, and rich reporting.

---

## ✨ Key Features

- **Wazuh Integration:** Natively connects to the Wazuh Manager API to automatically fetch, parse, and synchronize security alerts.
- **Kanban Alert Board:** A sleek, drag-and-drop interactive board for L1/L2 analysts to triage, acknowledge, and escalate incidents.
- **Advanced Notification System:** Real-time, in-app notification bells and automated email dispatching whenever an alert is assigned to an analyst.
- **Role-Based Access Control (RBAC):** Granular permissions ensuring L1 analysts, L2 analysts, Managers, and Admins only see what they need to.
- **Dynamic Settings Manager:** Centralized configuration panel to handle SLAs, escalation rules, alert sources, and platform aesthetics.
- **Comprehensive Reporting:** Export security analytics and analyst performance metrics directly to PDF or CSV.
- **Audit Logging:** Every status change, assignment, and configuration tweak is securely logged for compliance.

---

## 🛠️ Technology Stack

- **Backend:** Python, Django
- **Database:** PostgreSQL (Production), SQLite (Development)
- **Frontend:** HTML5, modern Vanilla CSS (Glassmorphism design), Bootstrap 5
- **SIEM Engine:** Wazuh API
- **Deployment:** Nginx, Gunicorn

---

## 🚀 Quickstart

1. **Clone the repository:**
   ```bash
   git clone https://github.com/boniyeamincse/ariba_soc.git
   cd ariba_soc
   ```

2. **Set up virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Database & Migrations:**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

4. **Run the Development Server:**
   ```bash
   python manage.py runserver 0.0.0.0:8090
   ```

*(For full setup, including environment variables and Wazuh credentials, please refer to the Installation Guide.)*

---

## 📚 Documentation

The Ariba SOC platform comes with a comprehensive 12-part documentation suite located in the `docs/guide/` directory.

- [Installation Guide](docs/guide/installation-guide.md)
- [Architecture Overview](docs/guide/architecture-guide.md)
- [SOC L1 Analyst Guide](docs/guide/soc-l1-guide.md)
- [SOC L2 Analyst Guide](docs/guide/soc-l2-guide.md)
- [Admin & Settings Guide](docs/guide/settings-guide.md)
- [Wazuh API Setup](docs/guide/wazuh-api-setup-guide.md)

---

## 📄 License

This project is proprietary and intended for authorized SOC environments. All rights reserved.
