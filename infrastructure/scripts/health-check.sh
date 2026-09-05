#!/bin/bash

cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "======================================"
echo " SOC Stack Health Check "
echo "======================================"

echo -e "\n[1] Docker Compose Services Status:"
docker compose ps

echo -e "\n[2] Checking Wazuh Manager API..."
MGR_STATUS=$(curl -k -s -o /dev/null -w "%{http_code}" https://localhost:55000 || echo "failed")
if [[ "$MGR_STATUS" == "401" || "$MGR_STATUS" == "200" ]]; then
    echo -e "Wazuh Manager API: ${GREEN}Online${NC}"
else
    echo -e "Wazuh Manager API: ${RED}Offline/Unreachable ($MGR_STATUS)${NC}"
fi

echo -e "\n[3] Checking Wazuh Indexer..."
IDX_STATUS=$(curl -k -s -o /dev/null -w "%{http_code}" https://localhost:9200 || echo "failed")
if [[ "$IDX_STATUS" == "401" || "$IDX_STATUS" == "200" ]]; then
    echo -e "Wazuh Indexer: ${GREEN}Online${NC}"
else
    echo -e "Wazuh Indexer: ${RED}Offline/Unreachable ($IDX_STATUS)${NC}"
fi

echo -e "\n[4] Checking Ariba SOC Dashboard..."
SOC_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:80 || echo "failed")
if [[ "$SOC_STATUS" == "200" || "$SOC_STATUS" == "301" || "$SOC_STATUS" == "302" ]]; then
    echo -e "Ariba SOC: ${GREEN}Online${NC}"
else
    echo -e "Ariba SOC: ${RED}Offline/Unreachable ($SOC_STATUS)${NC}"
fi

echo -e "\nHealth check complete!"
