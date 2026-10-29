# 👥 User Guide: 05. Reporting & Data Exports

## 1. Exporting Filtered Alerts as CSV
1. In the **Alert Table**, apply any desired filters (e.g., date range, specific rule ID, hostname, or severity).
2. Click the **Export CSV** button in the filter bar.
3. The platform downloads a structured CSV file containing alert metadata, IDs, IPs, usernames, verdicts, risk scores, and SLA statuses.

---

## 2. Generating Executive PDF Reports
Ariba SOC includes built-in ReportLab and xhtml2pdf rendering engines for generating professional SOC executive reports:
1. Apply your desired filters on the Alert Table or open **Reports** (`/reports/`).
2. Click **Export PDF**.
3. A styled PDF is generated with:
   - Official Ariba SOC security header.
   - Severity breakdown charts and summary statistics.
   - High and Critical threat tables with MITRE ATT&CK technique mappings.
   - Generation timestamp and analyst audit footer.
