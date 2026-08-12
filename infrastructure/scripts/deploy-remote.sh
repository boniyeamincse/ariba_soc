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

echo "[1/4] SSH-ing into $SERVER to fetch latest infrastructure files..."
ssh $SERVER "cd $INFRA_DIR && git pull origin main"

echo "[2/4] Pulling latest Docker images on the remote server..."
ssh $SERVER "cd $INFRA_DIR && docker compose -f docker-compose.prod.yml pull"

echo "[3/4] Recreating containers with zero-downtime strategy..."
ssh $SERVER "cd $INFRA_DIR && docker compose -f docker-compose.prod.yml up -d web scheduler nginx"

echo "[4/4] Running health checks..."
ssh $SERVER "cd $INFRA_DIR && ./scripts/health-check.sh"

echo "======================================"
echo " Deployment Successful! "
echo "======================================"
