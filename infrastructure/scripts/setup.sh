#!/bin/bash
set -e

# Change to the infrastructure directory
cd "$(dirname "$0")/.."

echo "Checking host prerequisites..."
MAX_MAP_COUNT=$(sysctl -n vm.max_map_count || echo 0)
if [ "$MAX_MAP_COUNT" -lt 262144 ]; then
    echo "ERROR: vm.max_map_count is too low ($MAX_MAP_COUNT). It must be at least 262144 for OpenSearch/Wazuh Indexer."
    echo "Please run: sudo sysctl -w vm.max_map_count=262144"
    exit 1
fi

echo "Generating Wazuh Indexer certificates..."
# This generates certs in the config folder if they don't already exist
docker compose -f generate-indexer-certs.yml run --rm generator

echo "Starting unified SOC stack (Wazuh + Ariba SOC)..."
if [ ! -d "../ariba_soc" ] && [ -f "docker-compose.prod.yml" ]; then
    echo "Production environment detected. Using docker-compose.prod.yml"
    docker compose -f docker-compose.prod.yml up -d
else
    echo "Development environment detected. Using docker-compose.yml with --build"
    docker compose up --build -d
fi

echo "Waiting for web service to be healthy before seeding..."
# We sleep a bit to give time for db and web to start, though ideally we'd use a healthcheck
sleep 20
docker compose exec -T web python seed_wazuh_config.py || echo "Warning: seeding failed, perhaps db isn't ready?"

echo "SOC stack is starting up!"
echo "Wazuh Dashboard: https://localhost (allow a few minutes for OpenSearch to start)"
echo "Ariba SOC Dashboard: http://localhost"
