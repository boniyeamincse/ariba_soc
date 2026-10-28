#!/bin/bash
set -e

cd "$(dirname "$0")/.."

BACKUP_ID=$1

if [ -z "$BACKUP_ID" ]; then
    echo "Usage: ./scripts/restore.sh <timestamp>"
    echo "Example: ./scripts/restore.sh 20261028_120000"
    echo "Available backups:"
    ls -1 backups/ 2>/dev/null || echo "No backups found."
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
echo "WARNING: This will overwrite your current database and configurations."
read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore aborted."
    exit 1
fi

echo "[1] Restoring configurations..."
if [ -f "$BACKUP_DIR/soc_config.tar.gz" ]; then
    tar -xzf "$BACKUP_DIR/soc_config.tar.gz"
    echo " -> Configurations restored successfully."
elif [ -f "$BACKUP_DIR/wazuh_config.tar.gz" ]; then
    tar -xzf "$BACKUP_DIR/wazuh_config.tar.gz"
    echo " -> Wazuh configs restored successfully."
fi

echo "[2] Restoring Ariba SOC Database..."
if [ -f "$BACKUP_DIR/ariba_soc_db.sql" ]; then
    DB_CONTAINER=$(docker compose ps -q db 2>/dev/null || true)
    if [ -n "$DB_CONTAINER" ]; then
        DB_USER=$(grep '^DATABASE_USER=' .env 2>/dev/null | cut -d '=' -f2 || echo "ariba_soc")
        cat "$BACKUP_DIR/ariba_soc_db.sql" | docker compose exec -T db psql -U "$DB_USER" -d postgres
        echo " -> Database restored successfully."
    else
        echo " -> ERROR: Database container is not running! Please start the stack first."
    fi
else
    echo " -> WARNING: ariba_soc_db.sql not found in backup."
fi

echo "[3] Restarting services to apply changes..."
docker compose restart

echo "======================================"
echo " Restore completed."
echo "======================================"
