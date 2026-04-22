#!/bin/bash
set -euo pipefail

PROJECT_DIR="/root/dkinvite"
BACKUP_ROOT="/root/backups/dkinvite"
LATEST_DIR="$BACKUP_ROOT/latest"
LOG_FILE="$BACKUP_ROOT/backup.log"
TS="$(date '+%F %T')"

mkdir -p "$BACKUP_ROOT"

TMP_DIR="$(mktemp -d)"

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

echo "[$TS] START backup" >> "$LOG_FILE"

cp -a "$PROJECT_DIR/Dockerfile" "$TMP_DIR/"
cp -a "$PROJECT_DIR/docker-compose.yml" "$TMP_DIR/"
cp -a "$PROJECT_DIR/app" "$TMP_DIR/"

rm -rf "$LATEST_DIR"
mkdir -p "$LATEST_DIR"

cp -a "$TMP_DIR/." "$LATEST_DIR/"

{
    echo "[$TS] Backup updated: $LATEST_DIR"
    ls -lah "$LATEST_DIR"
    echo
} >> "$LOG_FILE"

echo "Бэкап обновлен: $LATEST_DIR"
