#!/bin/bash
# ==============================================================================
# Ariba SOC - Wazuh Agent Health Check & Verification Tool
# ==============================================================================

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================================="
echo "         ARIBA SOC - AGENT VERIFICATION TOOL              "
echo "=========================================================="

# 1. Check Agent Service
echo -n "[1] Checking wazuh-agent daemon... "
if systemctl is-active --quiet wazuh-agent; then
    echo -e "${GREEN}ACTIVE & RUNNING${NC}"
else
    echo -e "${RED}INACTIVE / STOPPED${NC}"
fi

# 2. Check Connection in Logs
echo -n "[2] Checking Server Connection... "
if grep -q "Connected to the server" /var/ossec/logs/ossec.log 2>/dev/null; then
    echo -e "${GREEN}CONNECTED${NC}"
    tail -n 50 /var/ossec/logs/ossec.log | grep -E "Connected to the server|Connected to" | tail -n 1
else
    echo -e "${YELLOW}WAITING / CHECK LOGS${NC}"
fi

# 3. Check Auditd Service & Rules
echo -n "[3] Checking auditd and PHP2Shell rules... "
if command -v auditctl &> /dev/null; then
    if auditctl -l | grep -q "audit-wazuh-c"; then
        echo -e "${GREEN}LOADED${NC}"
        auditctl -l | grep "audit-wazuh-c"
    else
        echo -e "${RED}RULE NOT LOADED (Run: sudo augenrules --load)${NC}"
    fi
else
    echo -e "${YELLOW}AUDITD NOT INSTALLED${NC}"
fi

# 4. Check Custom SCA Policy
echo -n "[4] Checking Custom SCA Policy (php2shell_mitigations.yml)... "
if [ -f "/var/ossec/etc/custom-sca-files/php2shell_mitigations.yml" ]; then
    echo -e "${GREEN}EXISTS & ACCESSIBLE${NC}"
else
    echo -e "${RED}MISSING (/var/ossec/etc/custom-sca-files/php2shell_mitigations.yml)${NC}"
fi

# 5. Check FIM Web Root Monitoring
echo -n "[5] Checking FIM web root config... "
if grep -q "/var/www/html" /var/ossec/etc/ossec.conf 2>/dev/null; then
    echo -e "${GREEN}CONFIGURED${NC}"
else
    echo -e "${YELLOW}/var/www/html NOT in ossec.conf${NC}"
fi

echo "=========================================================="
echo " Recent Agent Log Entries:"
echo "=========================================================="
tail -n 10 /var/ossec/logs/ossec.log 2>/dev/null || echo "No logs found."
echo "=========================================================="
