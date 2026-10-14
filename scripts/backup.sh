#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
chmod 700 backups
backup_file="backups/tg-signer-$(date +%Y%m%d-%H%M%S).tar.gz"
was_running="$(docker compose ps --status running -q dashboard)"
resume() { if [ -n "$was_running" ]; then docker compose start dashboard; fi; }
trap resume EXIT
if [ -n "$was_running" ]; then docker compose stop dashboard; fi
umask 077
tar -czf "$backup_file" data
echo "Backup written to $backup_file"
