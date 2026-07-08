# Escalation Guide

## Manual Escalation
If an L1 Analyst cannot resolve an alert within 15 minutes, or if the alert involves critical infrastructure, they must escalate it.
1. Open the alert editor.
2. Change Status to `Escalated`.
3. Change Assignee to an L2 Analyst or Team Lead.

## Automated Escalation
Ariba SOC can automatically escalate alerts based on predefined rules.
1. Go to `Settings -> Escalation Settings`.
2. Create a rule (e.g., "If Severity == Critical AND Source == DomainController").
3. Set the target assignee (e.g., `soc_manager`).
4. The system will automatically reassign these alerts upon ingestion.
