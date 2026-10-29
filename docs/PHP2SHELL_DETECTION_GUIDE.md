# 🛡️ PHP2Shell Remote Code Execution Detection Guide (CVE-2026-109618 & CVE-2026-109619)

Official Wazuh Advisory & Detection Architecture:  
Reference: [Detecting PHP2Shell remote code execution with Wazuh (Wazuh Blog, Oct 2026)](https://wazuh.com/blog/detecting-php2shell-remote-code-execution-with-wazuh/)

---

## 📌 1. Threat Overview
- **Vulnerabilities:** `CVE-2026-109618` & `CVE-2026-109619`
- **CVSS Score:** 9.2 (Critical)
- **Impact:** Unauthenticated Remote Code Execution (RCE) via memory corruption in PHP (especially Apache `mod_php`).
- **Attack Indicators:**
  - Repeated PHP fatal memory exhaustion errors (`Allowed memory size exhausted`).
  - PHP maximum execution time exceeded errors.
  - Unexpected process execution under web server user (`www-data` / `apache`, EUID 33).
  - Web shell creation/modification (`.php`, `.phtml`, `.phar`) under web roots (e.g. `/var/www/html`).

---

## 📌 2. Wazuh Manager Custom Rules

The detection rules are configured in `/var/ossec/etc/rules/php2shell_rules.xml`:

| Rule ID | Level | Description | MITRE ATT&CK |
|---|---|---|---|
| **100200** | 7 | PHP2Shell precursor: PHP memory exhaustion fatal error | T1190 |
| **100201** | 7 | PHP2Shell precursor: PHP maximum execution time exceeded | T1190 |
| **100202** | 12 | PHP2Shell active attack: Multiple memory exhaustion errors from same IP | T1190 |
| **100210** | 12 | PHP2Shell post-exploitation: `www-data` (EUID 33) executed a command | T1059.004 |
| **100220** | 12 | PHP2Shell post-exploitation: New PHP file created in `/var/www/html` | T1505.003 |
| **100221** | 10 | PHP2Shell post-exploitation: Existing PHP file modified in `/var/www/html` | T1505.003 |

---

## 📌 3. Monitored Web Server (Agent) Configuration

To enable complete end-to-end detection on your PHP / Apache web servers, apply the following on the monitored endpoints:

### Step 3.1: Linux Auditd Rules
Add `/etc/audit/rules.d/wazuh-php2shell.rules`:
```bash
-a always,exit -F arch=b64 -S execve -F euid=33 -k audit-wazuh-c
-a always,exit -F arch=b32 -S execve -F euid=33 -k audit-wazuh-c
```
Reload auditd rules:
```bash
sudo augenrules --load
# Verify:
sudo auditctl -l | grep audit-wazuh-c
```

### Step 3.2: Custom SCA Policy
Copy `config/wazuh_cluster/sca/php2shell_mitigations.yml` to the agent:
```bash
sudo mkdir -p /var/ossec/etc/custom-sca-files
sudo cp php2shell_mitigations.yml /var/ossec/etc/custom-sca-files/
sudo chown -R wazuh:wazuh /var/ossec/etc/custom-sca-files/
```

### Step 3.3: Wazuh Agent `ossec.conf` Configuration
Ensure the following blocks are active in `/var/ossec/etc/ossec.conf`:
```xml
<ossec_config>
  <!-- Apache Error Log Collection -->
  <localfile>
    <log_format>apache</log_format>
    <location>/var/log/apache2/error.log</location>
  </localfile>

  <!-- Audit Log Collection -->
  <localfile>
    <log_format>audit</log_format>
    <location>/var/log/audit/audit.log</location>
  </localfile>

  <!-- Web Root Real-Time FIM -->
  <syscheck>
    <directories realtime="yes" check_all="yes">/var/www/html</directories>
  </syscheck>

  <!-- Custom SCA Policy Evaluation -->
  <sca>
    <policies>
      <policy enabled="yes">/var/ossec/etc/custom-sca-files/php2shell_mitigations.yml</policy>
    </policies>
  </sca>
</ossec_config>
```
Restart Wazuh agent:
```bash
sudo systemctl restart wazuh-agent
```

---

## 📌 4. Verification & Attack Emulation

### A. Precursor Test (Memory Exhaustion)
Send test requests causing memory exhaustion:
```bash
curl -s "http://<TARGET_SERVER>/php2shell-test.php"
```
Expect **Rule 100200** (Level 7) alert. Repeating 5 times triggers **Rule 100202** (Level 12).

### B. Post-Exploitation Test (EUID 33 Command Execution)
Execute command as `www-data`:
```bash
sudo -u www-data /bin/sh -c 'id; uname -a'
```
Expect **Rule 100210** (Level 12) alert.

### C. FIM Web Shell Test
Create a test PHP file in the web root:
```bash
echo '<?php phpinfo(); ?>' | sudo tee /var/www/html/shell.php
```
Expect **Rule 100220** (Level 12) alert.
