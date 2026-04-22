#!/usr/bin/env bash
set -e

if [ -z "$1" ]; then
  echo "Usage: ./restore_qrs.sh /path/to/qrs.tar.gz"
  exit 1
fi

rm -rf /root/dkinvite/app/static/qrs
mkdir -p /root/dkinvite/app/static
tar -xzf "$1" -C /root/dkinvite/app/static

echo "QR restored"
ls -lah /root/dkinvite/app/static/qrs
