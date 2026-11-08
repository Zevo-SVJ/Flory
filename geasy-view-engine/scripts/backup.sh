#!/usr/bin/env bash
# Daily logical backup of Postgres with 14-day rotation of OLD BACKUP FILES ONLY (backups/geasy-*.sql.gz).
# Run from anywhere; schedule with cron:  0 4 * * * /opt/geasy/scripts/backup.sh >> /var/log/geasy-backup.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
tmp="backups/.geasy-${stamp}.partial"
final="backups/geasy-${stamp}.sql.gz"

docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' | gzip -9 > "$tmp"
# gzip of an empty dump is ~20 bytes: refuse to publish a backup that contains nothing
if [ "$(gzip -dc "$tmp" | wc -c)" -lt 1000 ]; then
  echo "backup looks empty, kept as $tmp for inspection" >&2
  exit 1
fi
mv "$tmp" "$final"
find backups -maxdepth 1 -type f -name 'geasy-*.sql.gz' -mtime +14 -delete
echo "ok $final ($(du -h "$final" | cut -f1))"
