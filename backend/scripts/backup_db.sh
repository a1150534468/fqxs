#!/bin/bash
# Database backup script for TomatoFiction platform

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_NAME="${DB_NAME:-tomato_fiction}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-rootpassword}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_${DB_NAME}_${TIMESTAMP}.sql"
BACKUP_FILE_GZ="${BACKUP_FILE}.gz"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting database backup..."

# Perform backup
mysqldump \
  --host="$DB_HOST" \
  --port="$DB_PORT" \
  --user="$DB_USER" \
  --password="$DB_PASSWORD" \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  --databases "$DB_NAME" \
  > "$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_FILE"

# Calculate backup size
BACKUP_SIZE=$(du -h "$BACKUP_FILE_GZ" | cut -f1)

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup completed: $BACKUP_FILE_GZ (${BACKUP_SIZE})"

# Clean up old backups
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaning up backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "backup_${DB_NAME}_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete

# List recent backups
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Recent backups:"
ls -lh "$BACKUP_DIR"/backup_${DB_NAME}_*.sql.gz | tail -5

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup process completed successfully"
