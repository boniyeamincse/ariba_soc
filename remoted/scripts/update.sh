#!/bin/bash
set -e

cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
NC='\033[0m'

echo "======================================"
echo "    UPDATING ARIBA SOC CONTAINERS     "
echo "======================================"

echo "[1/3] Pulling latest images from Docker Hub..."
docker compose pull web scheduler

echo "[2/3] Recreating web and scheduler containers..."
docker compose up -d --no-deps web scheduler nginx

echo "[3/3] Checking container status..."
docker compose ps web scheduler

echo -e "\n${GREEN}Update completed successfully!${NC}"
