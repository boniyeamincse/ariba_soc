# Alert Triage Guide

## Standard Operating Procedure (SOP)

### 1. Detection
An alert is ingested from Wazuh or another source and appears in the `New` column of the Alert Board.

### 2. Acknowledgment
An analyst reviews the alert, changes the status to `In Progress`, and assigns it to themselves. This stops the SLA clock for "Time to Triage".

### 3. Investigation
The analyst reviews the raw payload. 
- Are there associated past alerts?
- Is this a known vulnerability scanner IP?

### 4. Verdict Assignment
The analyst sets a Verdict:
- **True Positive:** Genuine threat.
- **False Positive:** Legitimate activity flagged incorrectly.
- **Benign:** Known, expected behavior.

### 5. Resolution
The analyst changes the status to `Closed`. If it was a True Positive, remediation steps must be logged.
