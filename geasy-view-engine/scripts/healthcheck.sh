#!/usr/bin/env bash
# External monitor: exit 1 if the public site or the webhook worker is unhealthy.
# Cron every 5 min, and ping an uptime service on success, e.g.:
#   */5 * * * * /opt/geasy/scripts/healthcheck.sh && curl -fsS https://hc-ping.com/<your-uuid> >/dev/null
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
curl -fsS --max-time 10 "${PUBLIC_BASE_URL}/api/health" >/dev/null || { echo "web unhealthy"; exit 1; }
docker compose exec -T worker node -e "fetch('http://127.0.0.1:4000/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))" || { echo "worker unhealthy"; exit 1; }
echo ok
