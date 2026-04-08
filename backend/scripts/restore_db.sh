#!/bin/bash
# Database restore script for TomatoFiction platform

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_NAME="${DB_NAME:-tomato_fiction}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-rootpassword}"

# Check if backup file is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <backup_file.sql.gz>"
  echo ""
  echo "Available backups:"
  ls -lh "$BACKUP_DIR"/backup_${DB_NAME}_*.sql.gz 2>/dev/null || echo "No backups found"
  exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
  echo "Error: Backup file not found: $BACKUP_FILE"
  exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting database restore from: $BACKUP_FILE"

# Confirm restore
read -p "This will overwrite the current database. Are you sure? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "Restore cancelled"
  exit 0
fi

# Create temporary directory
TEMP_DIR=$(mktemp -d)
TEMP_SQL="$TEMP_DIR/restore.sql"

# Decompress backup
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Decompressing backup..."
gunzip -c "$BACKUP_FILE" > "$TEMP_SQL"

# Restore database
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restoring database..."
mysql \
  --host="$DB_HOST" \
  --port="$DB_PORT" \
  --user="$DB_USER" \
  --password="$DB_PASSWORD" \
  < "$TEMP_SQL"

# Clean up
rm -rf "$TEMP_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Database restore completed successfully"
