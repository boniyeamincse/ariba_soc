#!/bin/bash
set -e

# Change to the infrastructure directory
cd "$(dirname "$0")/.."

BACKUP_ID=$1

if [ -z "$BACKUP_ID" ]; then
    echo "Usage: ./scripts/restore.sh <timestamp>"
    echo "Example: ./scripts/restore.sh 20260812_002800"
    echo "Available backups:"
    ls -1 backups/
    exit 1
fi

BACKUP_DIR="backups/$BACKUP_ID"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "ERROR: Backup directory $BACKUP_DIR does not exist."
    exit 1
fi

echo "======================================"
echo " SOC Stack Restore ($BACKUP_ID) "
echo "======================================"
echo "WARNING: This will overwrite your current database and Wazuh configurations."
read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore aborted."
    exit 1
fi

echo "[1] Restoring Wazuh configurations..."
if [ -f "$BACKUP_DIR/wazuh_config.tar.gz" ]; then
    # Extract the tarball which contains the config/ directory
    tar -xzf "$BACKUP_DIR/wazuh_config.tar.gz"
    echo " -> Wazuh configs restored successfully."
else
    echo " -> WARNING: wazuh_config.tar.gz not found in backup."
fi

echo "[2] Restoring Ariba SOC Database..."
if [ -f "$BACKUP_DIR/ariba_soc_db.sql" ]; then
    DB_CONTAINER=$(docker-compose ps -q db)
    if [ -n "$DB_CONTAINER" ]; then
        # Drop existing connections and restore
        echo " -> Loading SQL dump into database container..."
        cat "$BACKUP_DIR/ariba_soc_db.sql" | docker-compose exec -T db psql -U ariba_soc -d postgres
        echo " -> Database restored successfully."
    else
        echo " -> ERROR: Database container is not running! Please start the stack first."
    fi
else
    echo " -> WARNING: ariba_soc_db.sql not found in backup."
fi

echo "[3] Restarting services to apply changes..."
docker-compose restart

echo "======================================"
echo " Restore completed."
echo "======================================"
