#!/bin/bash

cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

HTTP_PORT=$(grep '^HTTP_PORT=' .env 2>/dev/null | cut -d '=' -f2 || echo "80")
[ -z "$HTTP_PORT" ] && HTTP_PORT=80

echo "======================================"
echo "    ARIBA SOC STACK HEALTH CHECK      "
echo "======================================"

echo -e "\n[1] Docker Compose Services Status:"
docker compose ps

echo -e "\n[2] Checking Wazuh Manager API (port 55000)..."
MGR_STATUS=$(curl -k -s -o /dev/null -w "%{http_code}" https://localhost:55000 || echo "failed")
if [[ "$MGR_STATUS" == "401" || "$MGR_STATUS" == "200" ]]; then
    echo -e "Wazuh Manager API: ${GREEN}Online (HTTP $MGR_STATUS)${NC}"
else
    echo -e "Wazuh Manager API: ${RED}Offline/Unreachable ($MGR_STATUS)${NC}"
fi

echo -e "\n[3] Checking Wazuh Indexer (port 9200)..."
IDX_STATUS=$(curl -k -s -o /dev/null -w "%{http_code}" https://localhost:9200 || echo "failed")
if [[ "$IDX_STATUS" == "401" || "$IDX_STATUS" == "200" ]]; then
    echo -e "Wazuh Indexer:     ${GREEN}Online (HTTP $IDX_STATUS)${NC}"
else
    echo -e "Wazuh Indexer:     ${RED}Offline/Unreachable ($IDX_STATUS)${NC}"
fi

echo -e "\n[4] Checking Wazuh Dashboard (port 8443)..."
DASH_STATUS=$(curl -k -s -o /dev/null -w "%{http_code}" https://localhost:8443 || echo "failed")
if [[ "$DASH_STATUS" == "200" || "$DASH_STATUS" == "302" || "$DASH_STATUS" == "401" ]]; then
    echo -e "Wazuh Dashboard:   ${GREEN}Online (HTTP $DASH_STATUS)${NC}"
else
    echo -e "Wazuh Dashboard:   ${YELLOW}Starting/Unreachable ($DASH_STATUS)${NC}"
fi

echo -e "\n[5] Checking Ariba SOC Web (port $HTTP_PORT)..."
SOC_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${HTTP_PORT} || echo "failed")
if [[ "$SOC_STATUS" == "200" || "$SOC_STATUS" == "301" || "$SOC_STATUS" == "302" ]]; then
    echo -e "Ariba SOC Web:     ${GREEN}Online (HTTP $SOC_STATUS)${NC}"
else
    echo -e "Ariba SOC Web:     ${RED}Offline/Unreachable ($SOC_STATUS)${NC}"
fi

echo -e "\n======================================"
echo "Health check complete!"
echo "======================================"
