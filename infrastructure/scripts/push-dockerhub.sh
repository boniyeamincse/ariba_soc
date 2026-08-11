#!/bin/bash
set -e

cd "$(dirname "$0")/.."

echo "======================================"
echo " Push to Docker Hub "
echo "======================================"

echo "Building the Ariba SOC images..."
docker compose build web scheduler

echo "Pushing images to Docker Hub (boniyeamin/ariba_soc)..."
# Note: Ensure you are logged in to docker hub before running this (docker login)
docker compose push web scheduler

echo "======================================"
echo " Push complete! "
echo "======================================"
