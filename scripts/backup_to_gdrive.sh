#!/bin/bash
# ==============================================================================
# Stock Agent IDX — Automated Backup to Google Drive
# Backs up PostgreSQL (stockagent), Vector DB (vectoragent), .env, ML models, and 9router (AI Gateway)
# ==============================================================================
set -euo pipefail

PROJECT_DIR="/home/ubuntu/stock-agent-idx"
BACKUP_DIR="/tmp/stock_backup_$(date +%s)"
DATE=$(date +"%Y%m%d_%H%M%S")
ARCHIVE_NAME="stockagent_backup_${DATE}.tar.gz"
GDRIVE_REMOTE="${GDRIVE_REMOTE:-hamboo-sumupod-backup:VPS_StockAgent_Backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

mkdir -p "$BACKUP_DIR"
cd "$PROJECT_DIR"

cleanup() {
    rm -rf "$BACKUP_DIR"
}
trap cleanup EXIT

echo "=================================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting automated backup..."

# 1. Check if containers are running
if ! docker compose ps --services --filter "status=running" | grep -q "^postgres$"; then
    echo "ERROR: Service postgres is not running! Aborting."
    exit 1
fi

# 2. Dump PostgreSQL Database (stockagent)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Dumping main PostgreSQL database (stockagent)..."
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-stockuser}" "${POSTGRES_DB:-stockagent}" | gzip > "$BACKUP_DIR/db_stockagent.sql.gz"

# 3. Dump Vector PostgreSQL Database (vectoragent) if running
if docker compose ps --services --filter "status=running" | grep -q "^vector_postgres$"; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Dumping vector database (vectoragent)..."
    docker compose exec -T vector_postgres pg_dump -U vectoruser vectoragent | gzip > "$BACKUP_DIR/db_vectoragent.sql.gz"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Service vector_postgres not running, skipping vector dump."
fi

# 4. Copy configuration & models
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Collecting configuration and models..."
if [ -f .env ]; then
    cp .env "$BACKUP_DIR/.env"
fi

if [ -d models ]; then
    cp -r models "$BACKUP_DIR/models"
fi

# 5. Backup 9router data (AI Gateway database, keys & configuration)
if [ -d /home/ubuntu/.9router ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backing up 9router configuration & database..."
    tar --exclude="runtime/node_modules" --exclude="logs/*" -czf "$BACKUP_DIR/9router_backup.tar.gz" -C /home/ubuntu .9router
fi

# 6. Create compressed archive
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Creating compressed archive: $ARCHIVE_NAME..."
tar -czf "$BACKUP_DIR/$ARCHIVE_NAME" -C "$BACKUP_DIR" \
    --exclude="models/.git" \
    $(ls "$BACKUP_DIR" | grep -v "$ARCHIVE_NAME")

ARCHIVE_SIZE=$(du -h "$BACKUP_DIR/$ARCHIVE_NAME" | cut -f1)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Archive created successfully. Size: $ARCHIVE_SIZE"

# 6. Upload to Google Drive via rclone
if command -v rclone >/dev/null 2>&1; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Uploading to $GDRIVE_REMOTE..."
    rclone copy "$BACKUP_DIR/$ARCHIVE_NAME" "$GDRIVE_REMOTE" --stats 5s

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaning up old backups (> ${RETENTION_DAYS} days) on Google Drive..."
    rclone delete "$GDRIVE_REMOTE" --min-age "${RETENTION_DAYS}d" || true
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Remote retention cleanup completed."
else
    echo "WARNING: rclone is not installed or not in PATH! Archive saved locally at $BACKUP_DIR/$ARCHIVE_NAME"
    exit 2
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup process completed successfully!"
echo "=================================================="
