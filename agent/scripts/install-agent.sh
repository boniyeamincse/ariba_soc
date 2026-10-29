#!/bin/bash
# ==============================================================================
# Ariba SOC - Wazuh Agent Automated Installer & Hardener
# Compatible with: Ubuntu 20.04+, Debian 11+, RHEL/CentOS/Rocky 8+
# Usage: sudo ./install-agent.sh <WAZUH_MANAGER_IP> [AGENT_NAME]
# Example: sudo ./install-agent.sh 10.24.66.2 web-prod-01
# ==============================================================================

set -e

MANAGER_IP=$1
AGENT_NAME=${2:-$(hostname)}

if [ -z "$MANAGER_IP" ]; then
    echo "=========================================================="
    echo " ERROR: Wazuh Manager IP is required."
    echo " Usage:   sudo ./install-agent.sh <MANAGER_IP> [AGENT_NAME]"
    echo " Example: sudo ./install-agent.sh 10.24.66.2 $(hostname)"
    echo "=========================================================="
    exit 1
fi

if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run this script as root (sudo)."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================================="
echo "    ARIBA SOC - WAZUH AGENT INSTALLATION & ENROLLMENT     "
echo "=========================================================="
echo " Wazuh Manager: $MANAGER_IP"
echo " Agent Name:    $AGENT_NAME"
echo " OS:            $(uname -s) $(uname -r)"
echo "=========================================================="

# 1. Install Wazuh Agent if not installed
if ! command -v /var/ossec/bin/wazuh-control &> /dev/null; then
    echo "[1/6] Installing Wazuh Agent repository and package..."
    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y curl apt-transport-https gnupg lsb-release auditd
        curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | gpg --no-default-keyring --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import
        chmod 644 /usr/share/keyrings/wazuh.gpg
        echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" | tee /etc/apt/sources.list.d/wazuh.list
        apt-get update
        WAZUH_MANAGER="$MANAGER_IP" WAZUH_AGENT_NAME="$AGENT_NAME" apt-get install -y wazuh-agent
    elif command -v dnf &> /dev/null || command -v yum &> /dev/null; then
        rpm --import https://packages.wazuh.com/key/GPG-KEY-WAZUH
        cat > /etc/yum.repos.d/wazuh.repo << 'EOF'
[wazuh]
name=Wazuh repository
baseurl=https://packages.wazuh.com/4.x/yum/
gpgcheck=1
gpgkey=https://packages.wazuh.com/key/GPG-KEY-WAZUH
enabled=1
EOF
        WAZUH_MANAGER="$MANAGER_IP" WAZUH_AGENT_NAME="$AGENT_NAME" yum install -y wazuh-agent audit
    else
        echo "ERROR: Unsupported package manager. Please install wazuh-agent manually."
        exit 1
    fi
else
    echo "[1/6] Wazuh Agent is already installed."
fi

# 2. Configure ossec.conf
echo "[2/6] Configuring /var/ossec/etc/ossec.conf..."
if [ -f "$BASE_DIR/config/ossec.conf" ]; then
    sed "s/WAZUH_MANAGER_IP/$MANAGER_IP/g" "$BASE_DIR/config/ossec.conf" > /var/ossec/etc/ossec.conf
    chown root:wazuh /var/ossec/etc/ossec.conf
    chmod 640 /var/ossec/etc/ossec.conf
else
    echo "Warning: $BASE_DIR/config/ossec.conf not found. Using existing config."
    sed -i "s/<address>.*<\/address>/<address>$MANAGER_IP<\/address>/" /var/ossec/etc/ossec.conf
fi

# 3. Setup Custom SCA policy (PHP2Shell & Hardening)
echo "[3/6] Installing Custom SCA Policies..."
mkdir -p /var/ossec/etc/custom-sca-files
if [ -f "$BASE_DIR/sca/php2shell_mitigations.yml" ]; then
    cp "$BASE_DIR/sca/php2shell_mitigations.yml" /var/ossec/etc/custom-sca-files/
    chown -R root:wazuh /var/ossec/etc/custom-sca-files/
    chmod 640 /var/ossec/etc/custom-sca-files/*.yml
fi

# 4. Setup Linux Auditd Rules (Process Tracking & PHP2Shell)
echo "[4/6] Installing Auditd Rules for Web & Process Execution..."
mkdir -p /etc/audit/rules.d/
if [ -f "$BASE_DIR/auditd/wazuh-php2shell.rules" ]; then
    cp "$BASE_DIR/auditd/wazuh-php2shell.rules" /etc/audit/rules.d/
    if command -v augenrules &> /dev/null; then
        augenrules --load || true
    elif command -v service &> /dev/null; then
        service auditd restart || true
    fi
fi

# 5. Enable and Restart Services
echo "[5/6] Enabling and starting services..."
systemctl daemon-reload
systemctl enable wazuh-agent
systemctl restart wazuh-agent
systemctl enable auditd || true
systemctl restart auditd || true

# 6. Check Connection
echo "[6/6] Verifying Agent Status..."
sleep 3
if /var/ossec/bin/wazuh-control status | grep -q "running"; then
    echo "=========================================================="
    echo " SUCCESS: Wazuh Agent is running and connected!"
    echo " Agent Name: $AGENT_NAME"
    echo " Connected to Manager: $MANAGER_IP:1514"
    echo " Webroot FIM: /var/www/html (Realtime)"
    echo " Custom SCA: php2shell_mitigations.yml enabled"
    echo " Auditd Key: audit-wazuh-c loaded"
    echo "=========================================================="
else
    echo "WARNING: Agent process started but might still be handshaking."
    echo "Check logs: sudo tail -n 30 /var/ossec/logs/ossec.log"
fi
