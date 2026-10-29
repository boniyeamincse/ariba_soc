# 👥 User Guide: 02. Alert Triage & Deep-Dive Investigation

## 1. Alert Table Overview
The **Alert Table** is your mission control center:
- **Interactive Severity KPI Cards (Top):**
  - **Total Alerts:** Overall scope of alerts matching active date/filter.
  - **Critical (Red):** Pulse indicator when critical threats are present. Clicking filters the table directly without losing counts.
  - **High (Orange):** Severe violations requiring immediate attention.
  - **Medium (Yellow) & Low (Green):** Standard policy anomalies.
- **Global Search:** Search across Rule IDs, Hostnames, Usernames, Source/Destination IPs, Process Names, Command Lines, and Target File Paths (e.g., `/etc/shadow`, `anydesk`).

---

## 2. Five-Question Investigation Framework
When you click on any alert to open **Alert Detail** (`/alerts/<id>/`), the interface answers five critical operational questions:

1. **What happened?**
   - Alert Title, Wazuh Rule Level, Rule Description, MITRE ATT&CK Technique, and Risk Score.
2. **Where did it happen?**
   - Hostname, Agent Name, Agent IP, and Asset Criticality Multiplier (Mission-Critical vs Standard).
3. **Who / What initiated it?**
   - Username (e.g., `root`, `www-data`), Source IP (with GeoIP country badge), Process Name, Command Line, and Target File Path.
4. **Is it malicious?**
   - Integrated CTI / VirusTotal threat indicators, aggregated event counters, and risk score.
5. **What should we do next?**
   - Pre-mapped remediation guidelines, playbook steps, and one-click action buttons.

---

## 3. Investigating Enriched Telemetry
- **Raw JSON Log:** View the exact unprocessed log document received from Wazuh indexer.
- **Audit Logs:** Full history of which analyst viewed, acknowledged, or modified the alert.
- **FIM File Telemetry:** For file tampering alerts, examine original hash vs modified hash (MD5, SHA1, SHA256).
- **Network Telemetry:** Correlated source/destination ports and suspicious connections.

---

## 4. Bulk Operations
In the Alert Table, select multiple alerts using checkboxes to:
- Bulk **Acknowledge** or change Status (`In Progress`, `Pending`, etc.)
- Bulk **Assign** to yourself, an analyst, or a specific SOC team (e.g., Shift A, Incident Response).
- Bulk **Close** with Verdict (`False Positive`, `True Positive`, `Benign Positive`, etc.).
