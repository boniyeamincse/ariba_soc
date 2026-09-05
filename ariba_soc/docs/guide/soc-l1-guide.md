# SOC Tier 1 (L1) Analyst Guide

## Role Objective
L1 Analysts form the first line of defense. Your goal is to monitor incoming alerts, perform initial triage, and filter out obvious false positives before escalating genuine threats to L2.

## 1. Alert Monitoring
Monitor the **Alert Board** (Kanban view) or the **Alert Table**. Focus on alerts in the `New` column.

## 2. Initial Triage Workflow
1. Click the dropdown arrow on an alert row to expand its details.
2. Review the Hostname, Source, and raw log payload.
3. If the alert is a known false positive, update its Status to `Closed` and Verdict to `False Positive`.
4. If the alert is suspicious, update its Status to `In Progress` and assign it to yourself.

## 3. Escalation
If an alert requires deep forensic analysis or involves a critical system:
1. Edit the alert.
2. Change the Status to `Escalated`.
3. Select an L2 Analyst or Manager as the new Assignee.
4. Leave a comment detailing your initial findings.
