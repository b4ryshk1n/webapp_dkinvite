#!/usr/bin/env bash
set -e

BACKUP_DIR="/root/backups/dkinvite/latest"

if [ ! -d "$BACKUP_DIR" ]; then
  echo "Backup not found: $BACKUP_DIR"
  exit 1
fi

echo "Stopping containers..."
cd /root/dkinvite
docker-compose down || true

echo "Restoring files..."
cp "$BACKUP_DIR/Dockerfile" /root/dkinvite/Dockerfile
cp "$BACKUP_DIR/docker-compose.yml" /root/dkinvite/docker-compose.yml

rm -rf /root/dkinvite/app
cp -r "$BACKUP_DIR/app" /root/dkinvite/app

echo "Starting containers..."
cd /root/dkinvite
docker-compose build --no-cache
docker-compose up -d

echo "Restore completed from: $BACKUP_DIR"
