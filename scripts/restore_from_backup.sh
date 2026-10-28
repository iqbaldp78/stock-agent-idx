#!/bin/bash
# ==============================================================================
# Stock Agent IDX — Restore from Backup Archive
# Restores PostgreSQL, Vector DB, .env, ML models, and 9router (AI Gateway)
# Usage:
#   ./scripts/restore_from_backup.sh <path_to_archive_or_gdrive_filename>
# Examples:
#   ./scripts/restore_from_backup.sh stockagent_backup_20261028_120000.tar.gz
#   ./scripts/restore_from_backup.sh /tmp/stockagent_backup_20261028_120000.tar.gz
# ==============================================================================
set -euo pipefail

PROJECT_DIR="/home/ubuntu/stock-agent-idx"
RESTORE_ARG="${1:-}"
GDRIVE_REMOTE="${GDRIVE_REMOTE:-hamboo-sumupod-backup:VPS_StockAgent_Backups}"
TEMP_RESTORE_DIR="/tmp/stock_restore_$(date +%s)"

if [ -z "$RESTORE_ARG" ]; then
    echo "=================================================="
    echo "Usage: $0 <path_to_archive.tar.gz | gdrive_filename>"
    echo ""
    echo "Available backups on Google Drive:"
    if command -v rclone >/dev/null 2>&1; then
        rclone lsf "$GDRIVE_REMOTE" 2>/dev/null || echo "Unable to query Google Drive (check rclone config)."
    else
        echo "(rclone not installed)"
    fi
    echo "=================================================="
    exit 1
fi

cd "$PROJECT_DIR"
mkdir -p "$TEMP_RESTORE_DIR"

cleanup() {
    rm -rf "$TEMP_RESTORE_DIR"
}
trap cleanup EXIT

ARCHIVE_PATH="$RESTORE_ARG"

# If the archive doesn't exist locally, try downloading it from Google Drive
if [ ! -f "$ARCHIVE_PATH" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] File '$ARCHIVE_PATH' not found locally. Attempting to download from Google Drive..."
    if ! command -v rclone >/dev/null 2>&1; then
        echo "ERROR: rclone is not installed, cannot download from Google Drive."
        exit 1
    fi
    rclone copy "$GDRIVE_REMOTE/$RESTORE_ARG" "$TEMP_RESTORE_DIR/"
    ARCHIVE_PATH="$TEMP_RESTORE_DIR/$RESTORE_ARG"
fi

if [ ! -f "$ARCHIVE_PATH" ]; then
    echo "ERROR: Could not locate archive '$ARCHIVE_PATH'."
    exit 1
fi

echo "=================================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting restore from: $ARCHIVE_PATH"

# Extract archive
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Extracting archive..."
tar -xzf "$ARCHIVE_PATH" -C "$TEMP_RESTORE_DIR"

# 1. Restore .env
if [ -f "$TEMP_RESTORE_DIR/.env" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restoring .env configuration..."
    cp "$TEMP_RESTORE_DIR/.env" "$PROJECT_DIR/.env"
fi

# 2. Restore models/
if [ -d "$TEMP_RESTORE_DIR/models" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restoring models directory..."
    mkdir -p "$PROJECT_DIR/models"
    cp -r "$TEMP_RESTORE_DIR/models/"* "$PROJECT_DIR/models/"
fi

# 3. Ensure database containers are up
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting database containers..."
docker compose up -d postgres vector_postgres

echo "Waiting for PostgreSQL to be healthy..."
docker compose exec -T postgres sh -c 'until pg_isready -U "${POSTGRES_USER:-stockuser}" -d "${POSTGRES_DB:-stockagent}"; do sleep 2; done'

# 4. Restore main database
if [ -f "$TEMP_RESTORE_DIR/db_stockagent.sql.gz" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restoring database 'stockagent'..."
    gunzip -c "$TEMP_RESTORE_DIR/db_stockagent.sql.gz" | docker compose exec -T postgres psql -U "${POSTGRES_USER:-stockuser}" -d "${POSTGRES_DB:-stockagent}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Main database restored successfully!"
fi

# 5. Restore vector database if present
if [ -f "$TEMP_RESTORE_DIR/db_vectoragent.sql.gz" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restoring database 'vectoragent'..."
    gunzip -c "$TEMP_RESTORE_DIR/db_vectoragent.sql.gz" | docker compose exec -T vector_postgres psql -U vectoruser -d vectoragent
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Vector database restored successfully!"
fi

# 6. Restore 9router data if present
if [ -f "$TEMP_RESTORE_DIR/9router_backup.tar.gz" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restoring 9router data to /home/ubuntu/.9router..."
    mkdir -p /home/ubuntu/.9router
    tar -xzf "$TEMP_RESTORE_DIR/9router_backup.tar.gz" -C /home/ubuntu/
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 9router configuration and database restored!"
    if docker ps -a --format '{{.Names}}' | grep -q "^9router$"; then
        echo "Restarting 9router container to apply restored data..."
        docker restart 9router || true
    fi
fi

echo "=================================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] RESTORE COMPLETED SUCCESSFULLY!"
echo "You can now start all services with: docker compose up -d"
echo "=================================================="
