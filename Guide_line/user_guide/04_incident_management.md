# 👥 User Guide: 04. Incident Management & SLAs

## 1. When to Escalate to an Incident
An alert should be escalated to a formal **Incident** (`/incidents/create/`) when:
- Multiple correlated alerts indicate an active intrusion or lateral movement.
- Critical assets (e.g., Domain Controllers, Database Clusters, Production Web Gateways) are compromised.
- Malware (e.g., Ransomware, Cobalt Strike, PHP2Shell web shells) is actively executing.
- Data exfiltration or unauthorized privilege escalation is confirmed.

---

## 2. Incident Lifecycle
1. **Identification & Triage:** Incident title, severity level, affected business assets, and assigned Lead Investigator.
2. **Containment:** Document network isolation, firewall blocks, or endpoint quarantine.
3. **Eradication:** Removal of persistence artifacts, scheduled tasks, web shells, and compromised credentials.
4. **Recovery & Lessons Learned:** Restoring clean states and updating detection rules.

---

## 3. SLA Tracking & Breach Alarms
Ariba SOC automatically monitors two critical SLA thresholds:
- **Acknowledgment SLA (ACK):** Time from alert ingestion to an analyst taking ownership (`In Progress`).
- **Resolution SLA (RESOLVE):** Time from alert ingestion to final disposition (`Closed` or `Resolved`).

If an SLA breaches:
- The alert card displays a **Breached (Red)** badge.
- Audio and visual alarm notifications are broadcast to online SOC analysts.
- The alert can automatically escalate to L2/Management based on team policies.
