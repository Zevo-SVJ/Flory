#!/usr/bin/env bash
# GEASY VIEW ENGINE — one-command installer for a fresh Ubuntu/Debian VPS.
#
#   sudo ./install.sh                         # no domain needed: uses <ip>.sslip.io with a real HTTPS certificate
#   sudo ./install.sh --domain geasy.me.com   # your own domain (its A record must already point to this server)
#   sudo ./install.sh --bot-token 123456:ABC… # also registers your bot + webhook
#   options: --admin-email you@mail.com
#
# Idempotent: re-running keeps your existing .env (and therefore your secrets) and just rebuilds/updates.
set -euo pipefail

DOMAIN=""; BOT_TOKEN=""; ADMIN_EMAIL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --domain) DOMAIN="$2"; shift 2 ;;
    --bot-token) BOT_TOKEN="$2"; shift 2 ;;
    --admin-email) ADMIN_EMAIL="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

say()  { printf '\n\033[1;32m▸ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m! %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "Run as root: sudo ./install.sh"
cd "$(dirname "$0")"

# ── 1. Docker ───────────────────────────────────────────────
if ! command -v docker >/dev/null 2>&1; then
  say "Installing Docker"
  curl -fsSL https://get.docker.com | sh
fi
docker compose version >/dev/null 2>&1 || die "Docker Compose v2 is missing (install docker-compose-plugin)"
systemctl enable --now docker >/dev/null 2>&1 || true

# ── 2. Firewall (only if ufw is already active) ─────────────
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
  say "Opening ports 80/443 in ufw"
  ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null; ufw allow 443/udp >/dev/null
fi

# ── 3. Configuration (.env) ─────────────────────────────────
NEW_ENV=0
if [ -f .env ]; then
  say "Existing .env found: keeping your secrets"
else
  NEW_ENV=1
  say "Generating configuration"
  IP="$(curl -4fsS --max-time 10 https://api.ipify.org || true)"
  [ -n "$IP" ] || die "Could not detect the public IP; pass --domain"
  if [ -z "$DOMAIN" ]; then
    DOMAIN="$(echo "$IP" | tr . -).sslip.io"
    warn "No domain given: using $DOMAIN (free, real HTTPS certificate, resolves to $IP)"
  else
    RESOLVED="$(getent hosts "$DOMAIN" | awk '{print $1}' | head -n1 || true)"
    if [ "$RESOLVED" != "$IP" ]; then
      die "$DOMAIN resolves to '${RESOLVED:-nothing}' but this server is $IP. Fix the DNS A record, wait a few minutes, retry."
    fi
  fi
  [ -n "$ADMIN_EMAIL" ] || ADMIN_EMAIL="admin@${DOMAIN}"
  ADMIN_PASSWORD="$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-20)"
  PGPASS="$(openssl rand -hex 24)"
  umask 077
  cat > .env <<EOF
DOMAIN=${DOMAIN}
PUBLIC_BASE_URL=https://${DOMAIN}
POSTGRES_USER=geasy
POSTGRES_PASSWORD=${PGPASS}
POSTGRES_DB=geasy
ENCRYPTION_KEY=$(openssl rand -hex 32)
ADMIN_EMAIL=${ADMIN_EMAIL}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
LOG_LEVEL=info
EOF
  umask 022
fi
set -a; . ./.env; set +a

# ── 4. Build & start ────────────────────────────────────────
say "Building and starting the stack (first build takes a few minutes)"
docker compose up -d --build

say "Waiting for the application to become healthy"
ok=0
for _ in $(seq 1 90); do
  if [ "$(docker compose ps --format '{{.Health}}' web 2>/dev/null | head -n1)" = "healthy" ]; then ok=1; break; fi
  sleep 4
done
[ "$ok" -eq 1 ] || { docker compose logs --tail=40 worker web; die "The app did not become healthy. See logs above."; }

# ── 5. Admin account ────────────────────────────────────────
say "Creating the admin account"
docker compose --profile setup run --rm create-admin

# ── 6. Bot (optional here, can also be done in the dashboard) ──
if [ -n "$BOT_TOKEN" ]; then
  say "Registering the bot and the webhook"
  docker compose run --rm -e BOT_TOKEN="$BOT_TOKEN" worker node dist/scripts/set-bot.mjs || warn "Bot registration failed; you can retry from the dashboard (Settings)"
fi

# ── 7. Backups + monitoring (cron) ──────────────────────────
HERE="$(pwd)"
chmod +x scripts/backup.sh scripts/healthcheck.sh
cat > /etc/cron.d/geasy <<EOF
0 4 * * * root ${HERE}/scripts/backup.sh >> /var/log/geasy-backup.log 2>&1
*/5 * * * * root ${HERE}/scripts/healthcheck.sh >> /var/log/geasy-health.log 2>&1 || true
EOF
chmod 644 /etc/cron.d/geasy

# ── 8. HTTPS check ──────────────────────────────────────────
say "Checking HTTPS (certificate issuance can take up to a minute)"
https=0
for _ in $(seq 1 20); do
  if curl -fsS --max-time 8 "https://${DOMAIN}/api/health" >/dev/null 2>&1; then https=1; break; fi
  sleep 5
done

echo
echo "════════════════════════════════════════════════════════"
if [ "$https" -eq 1 ]; then echo "  GEASY VIEW ENGINE is online"; else echo "  Installed, but HTTPS is not answering yet (see 'docker compose logs caddy')"; fi
echo "  URL       : https://${DOMAIN}"
echo "  Email     : ${ADMIN_EMAIL}"
if [ "$NEW_ENV" -eq 1 ]; then
  echo "  Password  : ${ADMIN_PASSWORD}      (also stored in ${HERE}/.env)"
fi
echo "  Backups   : ${HERE}/backups (daily 04:00, kept 14 days) — copy them off the server"
echo "  IMPORTANT : save ENCRYPTION_KEY from ${HERE}/.env in your password manager"
echo "════════════════════════════════════════════════════════"
