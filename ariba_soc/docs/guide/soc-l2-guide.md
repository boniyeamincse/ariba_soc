# SOC Tier 2 (L2) Analyst Guide

## Role Objective
L2 Analysts handle complex incidents escalated by L1. Your goal is to investigate, determine the scope of the incident, and implement remediation strategies.

## 1. Handling Escalations
Monitor your **My Alerts** tab for alerts with the `Escalated` status. 
Alternatively, use the Kanban Board's `Escalated` column.

## 2. Deep Investigation
1. Review all L1 comments and notes.
2. Correlate the alert with external Threat Intelligence or internal logs.
3. Determine the final Verdict (`True Positive`, `Suspicious`, `Benign`).

## 3. Remediation & Closure
Once the threat is neutralized:
1. Ensure all actions taken are documented in the alert comments.
2. Change the Status to `Closed`.
3. If necessary, inform the SOC Manager to initiate an After-Action Report.
