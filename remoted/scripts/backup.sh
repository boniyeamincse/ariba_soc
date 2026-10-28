#!/bin/bash
set -e

cd "$(dirname "$0")/.."

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/$TIMESTAMP"

echo "======================================"
echo " SOC Stack Backup ($TIMESTAMP) "
echo "======================================"

mkdir -p "$BACKUP_DIR"

echo "[1] Backing up Ariba SOC PostgreSQL Database..."
DB_CONTAINER=$(docker compose ps -q db 2>/dev/null || true)
if [ -n "$DB_CONTAINER" ]; then
    DB_USER=$(grep '^DATABASE_USER=' .env 2>/dev/null | cut -d '=' -f2 || echo "ariba_soc")
    docker compose exec -T db pg_dumpall -c -U "$DB_USER" > "$BACKUP_DIR/ariba_soc_db.sql"
    echo " -> Database backed up successfully."
else
    echo " -> ERROR: Database container is not running! Cannot backup."
fi

echo "[2] Backing up configurations..."
if [ -d "config" ]; then
    tar -czf "$BACKUP_DIR/soc_config.tar.gz" config/
    echo " -> Configurations backed up successfully."
else
    echo " -> ERROR: config directory not found!"
fi

echo "======================================"
echo " Backup completed in: $BACKUP_DIR"
echo "======================================"
