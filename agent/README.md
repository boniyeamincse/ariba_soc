# Wazuh Agent Deployment & Configuration Package

This directory contains endpoint configuration templates, auditd rules, custom SCA policies, and automation scripts for monitored Linux/Windows agents reporting to the Ariba SOC Wazuh Cluster.

## Structure
- `auditd/` - Custom Linux Audit subsystem rule definitions (e.g., PHP2Shell execution tracking).
- `sca/` - Custom Security Configuration Assessment (SCA) yaml policies for endpoint compliance.
- `scripts/` - Automated agent enrollment, setup, and health check scripts.
- `config/` - Recommended endpoint `ossec.conf` blocks.
