#!/bin/bash
set -e

# Usage: ./deploy-to-server.sh user@server_ip [remote_dir]
SERVER=$1
REMOTE_DIR=${2:-"~/ariba_soc_deploy"}

if [ -z "$SERVER" ]; then
    echo "=========================================================="
    echo " ERROR: Please provide the SSH connection string."
    echo " Usage:   ./deploy-to-server.sh user@server_ip [target_dir]"
    echo " Example: ./deploy-to-server.sh root@192.168.1.100"
    echo "=========================================================="
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=========================================================="
echo " Ariba SOC Remote Deployment (Zero Source Code Exposure)  "
echo " Target Server:    $SERVER"
echo " Remote Directory: $REMOTE_DIR"
echo " Source Package:   $SCRIPT_DIR"
echo "=========================================================="

echo "[1/3] Ensuring remote directory exists..."
ssh "$SERVER" "mkdir -p $REMOTE_DIR"

echo "[2/3] Transferring Docker & Config files (NO raw source code)..."
rsync -avz --progress \
    --exclude=".env" \
    --exclude="backups/" \
    --exclude="config/wazuh_indexer_ssl_certs/" \
    "$SCRIPT_DIR/" "$SERVER:$REMOTE_DIR/"

echo "[3/3] Setting execute permissions on remote scripts..."
ssh "$SERVER" "chmod +x $REMOTE_DIR/scripts/*.sh"

echo "=========================================================="
echo " Files transferred successfully!"
echo "=========================================================="
echo "Next steps on your remote server:"
echo " 1. SSH into the server:"
echo "    ssh $SERVER"
echo ""
echo " 2. Navigate to deployment directory:"
echo "    cd $REMOTE_DIR"
echo ""
echo " 3. Create and customize .env (if first time):"
echo "    cp .env.example .env && nano .env"
echo ""
echo " 4. Run automated setup:"
echo "    ./scripts/setup.sh"
echo "=========================================================="
