# 💻 Developer Guide: 04. Wazuh Integration & Rule Authoring

## 1. Alert Ingestion & Normalization
The ingestion pipeline is implemented in [`ariba_soc/wazuh_integration/services.py`](file:///home/boni/Desktop/ariba_soc-main/ariba_soc/wazuh_integration/services.py):
- **Wazuh Indexer Querying:** Queries index pattern `wazuh-alerts-*` via OpenSearch REST API over HTTPS (`wazuh.indexer:9200`).
- **Telemetry Extraction & Normalization:**
  - `source_ip` / `destination_ip` (Suricata, Apache, Syslog, Netflow).
  - `username` / `process_user` (Auditd `audit.euid`/`audit.user`, Syslog, PAM, SSH).
  - `process_name` / `command_line` (Auditd `audit.exe`/`audit.command`, Sysmon).
  - `target_file` / `file_path` (Syscheck FIM, Auditd `audit.file.name`, Osquery).
  - `file_hash_md5` / `file_hash_sha1` / `file_hash_sha256` (Syscheck).
  - `mitre_id`, `mitre_tactic`, `mitre_technique` (Wazuh MITRE mapping).

### Management Command for Reparsing:
To backfill or re-parse fields from raw logs into normalized database columns:
```bash
docker exec infrastructure-web-1 python manage.py reparse_wazuh_alerts
```

---

## 2. Writing Custom Detection Rules
Custom Wazuh rules are located in:
- `infrastructure/config/wazuh_cluster/rules/`
- `remoted/config/wazuh_cluster/rules/`

### Adding a New Rule File:
1. Create a `.xml` file (e.g., `php2shell_rules.xml`).
2. Wrap rules inside a `<group name="your_group,">` tag.
3. Use unique IDs (100000+ for custom rules):
   ```xml
   <group name="web,custom,">
     <rule id="100200" level="7">
       <if_sid>30301</if_sid>
       <regex type="pcre2">Pattern here</regex>
       <description>Rule description</description>
       <mitre><id>T1190</id></mitre>
     </rule>
   </group>
   ```
4. Verify syntax inside the Wazuh container:
   ```bash
   docker exec infrastructure-wazuh.manager-1 /var/ossec/bin/wazuh-analysisd -t
   ```
5. Test rule logic using `wazuh-logtest`:
   ```bash
   echo "sample log" | docker exec -i infrastructure-wazuh.manager-1 /var/ossec/bin/wazuh-logtest
   ```
6. Reload Wazuh Manager:
   ```bash
   docker exec infrastructure-wazuh.manager-1 /var/ossec/bin/wazuh-control restart
   ```
