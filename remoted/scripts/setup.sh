#!/bin/bash
set -e

# Change to the root directory of the remoted package
cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================================="
echo "      ARIBA SOC & WAZUH - REMOTE SETUP SCRIPT            "
echo "=========================================================="

# 1. Check prerequisites
echo -e "\n[1/6] Checking host prerequisites..."
MAX_MAP_COUNT=$(sysctl -n vm.max_map_count 2>/dev/null || echo 0)
if [ "$MAX_MAP_COUNT" -lt 262144 ]; then
    echo -e "${YELLOW}Warning: vm.max_map_count is $MAX_MAP_COUNT (needs >= 262144 for Wazuh Indexer/OpenSearch).${NC}"
    echo "Attempting to increase vm.max_map_count..."
    if sudo sysctl -w vm.max_map_count=262144 2>/dev/null; then
        echo -e "${GREEN}vm.max_map_count successfully set to 262144.${NC}"
        # Make permanent if possible
        if [ -w /etc/sysctl.conf ]; then
            grep -qxF "vm.max_map_count=262144" /etc/sysctl.conf || echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf > /dev/null
        fi
    else
        echo -e "${RED}ERROR: Please run 'sudo sysctl -w vm.max_map_count=262144' and re-run this script.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}Host prerequisites OK (vm.max_map_count = $MAX_MAP_COUNT).${NC}"
fi

# 2. Check .env file
echo -e "\n[2/6] Checking environment configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}No .env found. Creating .env from .env.example...${NC}"
        cp .env.example .env
        chmod 600 .env
        echo -e "${YELLOW}Notice: Using default credentials from .env.example. Remember to edit .env for production security.${NC}"
    else
        echo -e "${RED}ERROR: .env or .env.example not found!${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}.env file found.${NC}"
fi

# 3. Generate Wazuh Certificates if not present
echo -e "\n[3/6] Checking Wazuh SSL certificates..."
if [ ! -f "config/wazuh_indexer_ssl_certs/root-ca.pem" ]; then
    echo "Generating certificates using wazuh-certs-generator..."
    mkdir -p config/wazuh_indexer_ssl_certs
    docker compose -f generate-indexer-certs.yml run --rm generator
    echo -e "${GREEN}Certificates generated successfully.${NC}"
else
    echo -e "${GREEN}Certificates already exist. Skipping generation.${NC}"
fi

# 4. Pull latest Docker images
echo -e "\n[4/6] Pulling Docker images from Docker Hub..."
docker compose pull

# 5. Start unified stack
echo -e "\n[5/6] Starting Ariba SOC & Wazuh containers..."
docker compose up -d

# 6. Wait for Web service and seed configuration
echo -e "\n[6/6] Waiting for services to become healthy..."
MAX_ATTEMPTS=30
ATTEMPT=0
WEB_READY=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT+1))
    STATUS=$(docker compose ps web --format "{{.Health}}" 2>/dev/null || echo "")
    if [[ "$STATUS" =~ "healthy" ]]; then
        WEB_READY=1
        break
    fi
    echo "Waiting for web container to report healthy... ($ATTEMPT/$MAX_ATTEMPTS)"
    sleep 5
done

if [ $WEB_READY -eq 1 ]; then
    echo -e "${GREEN}Web service is healthy!${NC}"
else
    echo -e "${YELLOW}Web container took longer than expected. Continuing with seeding...${NC}"
fi

echo "Seeding default Wazuh & SOC configurations..."
docker compose exec -T web python seed_wazuh_config.py || echo -e "${YELLOW}Notice: Seeding completed with warnings (or was already seeded).${NC}"

echo -e "\n=========================================================="
echo -e "${GREEN}      ARIBA SOC & WAZUH STACK IS UP AND RUNNING!        ${NC}"
echo "=========================================================="
HTTP_PORT=$(grep '^HTTP_PORT=' .env 2>/dev/null | cut -d '=' -f2 || echo "80")
[ -z "$HTTP_PORT" ] && HTTP_PORT=80

echo -e "Ariba SOC Dashboard:    ${GREEN}http://<your-server-ip>:${HTTP_PORT}${NC}"
echo -e "Wazuh Dashboard:        ${GREEN}https://<your-server-ip>:8443${NC}"
echo -e "Wazuh Manager API:      https://<your-server-ip>:55000"
echo "=========================================================="
echo "To check status:   ./scripts/health-check.sh"
echo "To view logs:      docker compose logs -f web"
echo "To stop:           docker compose down"
echo "=========================================================="
