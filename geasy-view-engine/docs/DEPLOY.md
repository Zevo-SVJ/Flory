# VPS deployment (Docker Compose)

Requirements: a VPS (1 vCPU / 1–2 GB RAM is enough), Docker + Compose v2, a domain whose A/AAAA record points to the VPS, ports 80 and 443 open.

## 1. Install

```bash
git clone <your repo> /opt/geasy && cd /opt/geasy/geasy-view-engine
cp .env.example .env
nano .env
```

Set at least: `DOMAIN`, `PUBLIC_BASE_URL` (`https://` + domain), `POSTGRES_PASSWORD`, `ENCRYPTION_KEY` (`openssl rand -hex 32`), `ADMIN_EMAIL`, `ADMIN_PASSWORD` (12+ chars).
**Back up `ENCRYPTION_KEY` somewhere safe**: without it the stored bot token / MTProto session cannot be decrypted (you would simply re-enter them).

```bash
docker compose up -d --build
docker compose --profile setup run --rm create-admin     # creates / resets the admin password
docker compose ps                                        # all "healthy"
```

Caddy obtains the HTTPS certificate on first request to your domain (keep the `caddy_data` volume).

## 2. Connect Telegram

1. @BotFather → `/newbot` → copy the token. (Group-privacy settings are irrelevant for channels.)
2. Dashboard → **Settings** → paste the token. GEASY verifies it with `getMe` and registers the webhook (`allowed_updates`: `channel_post`, `edited_channel_post`, `message_reaction_count`, `my_chat_member`). Settings shows pending updates and the last delivery error reported by Telegram.
3. In each channel: Administrators → Add administrator → your bot. Grant the minimum permissions Telegram allows (leave optional ones off).
4. Dashboard → **My Channels** → paste the channel link → **Connect**. Status must read *Connected*. A channel saved as *No access* is not monitored until the bot is an administrator; press **Verify access** afterwards.
5. **Automation** → per-channel switches (monitoring, stats, auto-reaction + emoji, notifications + destination chat id, interval, retries).

### Optional: views and forwards (MTProto)

```bash
docker compose run --rm -it worker node dist/scripts/mtproto-login.mjs
```

Enter your `api_id`/`api_hash` (my.telegram.org → API development tools), your phone, the code Telegram sends (and 2FA password if any). The account must be a member of the channels. The session is stored encrypted in Postgres. No restart needed: the worker reconnects when the credential changes. Then check **Activity Logs** after the first polling minute.
Use an account you control; do not use a number that is not yours.

## 3. Backups

```bash
chmod +x scripts/*.sh
crontab -e
0 4 * * *   /opt/geasy/geasy-view-engine/scripts/backup.sh      >> /var/log/geasy-backup.log 2>&1
*/5 * * * * /opt/geasy/geasy-view-engine/scripts/healthcheck.sh && curl -fsS https://hc-ping.com/<uuid> >/dev/null
```

`backup.sh` writes `backups/geasy-<UTC>.sql.gz` and removes backup files older than 14 days. Copy `backups/` off the server (rclone, rsync, S3…); a backup on the same disk does not survive the disk.

Restore (stops writers first):

```bash
docker compose stop web worker
gunzip -c backups/geasy-XXXX.sql.gz | docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'   # into an empty database
docker compose start worker web
```

To restore into the existing database, drop and recreate it first (`docker compose exec postgres psql -U <user> -d postgres -c 'DROP DATABASE <db> WITH (FORCE)' -c 'CREATE DATABASE <db>'`).

## 4. Operations

| Task | Command |
|---|---|
| Logs (structured JSON) | `docker compose logs -f worker web` |
| Update | `git pull && docker compose up -d --build` (migrations run at worker start) |
| Restart everything | `docker compose restart` (state is in Postgres/Redis volumes) |
| Rotate admin password | change it in Settings, or re-run `create-admin` (signs out all sessions) |
| Reboot the server | containers have `restart: unless-stopped`; Docker starts on boot (`systemctl enable docker`); monitoring resumes by itself |

Monitoring from the UI: **Overview** shows bot/worker/webhook/MTProto state and alerts; **Automation** shows queue depth; **Activity Logs** has everything with actors.

## 5. Troubleshooting

| Symptom | Check |
|---|---|
| No posts arrive | Settings → webhook "last delivery error"; bot is administrator (My Channels → Verify access); `PUBLIC_BASE_URL` is the exact public HTTPS URL; `docker compose logs worker` for `webhook rejected` |
| Channel stays *No access* | Bot must be an administrator, not just a member |
| Reactions skipped | Logs say the emoji is not allowed in the channel: pick one of the channel's enabled reactions |
| Views show `—` | MTProto not configured, or the account is not a member of the channel |
| 429 in logs | Handled automatically (queue pauses for `retry_after`); reduce polling frequency if frequent |
