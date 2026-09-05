#!/bin/bash
set -e

# Change to the infrastructure directory
cd "$(dirname "$0")/.."

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/$TIMESTAMP"

echo "======================================"
echo " SOC Stack Backup ($TIMESTAMP) "
echo "======================================"

mkdir -p "$BACKUP_DIR"

echo "[1] Backing up Ariba SOC PostgreSQL Database..."
# Determine the container name for the database. Usually something like 'infrastructure-db-1'
# If docker compose exec fails, it means the container is offline.
DB_CONTAINER=$(docker compose ps -q db)
if [ -n "$DB_CONTAINER" ]; then
    # Running pg_dumpall to backup everything
    # We use docker compose exec to run the command inside the container
    docker compose exec -T db pg_dumpall -c -U ariba_soc > "$BACKUP_DIR/ariba_soc_db.sql"
    echo " -> Database backed up successfully."
else
    echo " -> ERROR: Database container is not running! Cannot backup."
fi

echo "[2] Backing up Wazuh configurations..."
# We backup the entire config folder
if [ -d "config" ]; then
    tar -czf "$BACKUP_DIR/wazuh_config.tar.gz" config/
    echo " -> Wazuh configs backed up successfully."
else
    echo " -> ERROR: config directory not found!"
fi

echo "======================================"
echo " Backup completed in: $BACKUP_DIR"
echo "======================================"
