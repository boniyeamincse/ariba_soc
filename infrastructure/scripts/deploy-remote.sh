#!/bin/bash
set -e

# Usage: ./deploy-remote.sh user@10.10.10.10

SERVER=$1
INFRA_DIR="infrastructure"

if [ -z "$SERVER" ]; then
    echo "ERROR: Please provide the SSH connection string."
    echo "Usage: ./deploy-remote.sh user@server_ip"
    exit 1
fi

echo "======================================"
echo " Remote Deployment Script"
echo " Target: $SERVER"
echo "======================================"

INFRA_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "[1/4] Pushing latest infrastructure files to $SERVER..."
# Copy the infrastructure directory to the remote server, excluding large/local-only directories and root-owned certs
rsync -avz --exclude="data" --exclude="backups" --exclude=".env" --exclude="config/wazuh_indexer_ssl_certs" "$INFRA_DIR/" $SERVER:~/infrastructure/ || true

echo "[2/4] Pulling latest Docker images on the remote server..."
ssh $SERVER "cd ~/infrastructure && docker compose -f docker-compose.prod.yml pull"

echo "[3/4] Recreating containers with zero-downtime strategy..."
ssh $SERVER "cd ~/infrastructure && docker compose -f docker-compose.prod.yml up -d web scheduler nginx"

echo "[4/4] Running health checks..."
ssh $SERVER "cd ~/infrastructure && ./scripts/health-check.sh"

echo "======================================"
echo " Deployment Successful! "
echo "======================================"
