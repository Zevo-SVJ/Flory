# GEASY VIEW ENGINE

Private operations platform for your own Telegram channels: automatic post detection, real statistics with history, single-identity reaction management, per-channel automation. Runs 24/7 on a VPS with Docker Compose.

```
geasy-view-engine/
├─ migrations/          SQL migrations (applied automatically at worker start)
├─ src/app/             Next.js dashboard (8 pages + login), server actions
├─ src/worker/          Webhook receiver, BullMQ workers, schedulers, /health
├─ src/lib/             DB, crypto, Telegram clients, services (shared by web + worker)
├─ scripts/             migrate, create-user, mtproto-login, backup.sh, healthcheck.sh
├─ docker/Caddyfile     HTTPS reverse proxy
├─ docs/ARCHITECTURE.md Decisions, data sources, data flow, limits
├─ docs/DEPLOY.md       VPS runbook, backups, monitoring, restore
└─ tests/               Vitest (unit + integration on real Postgres/Redis) 
```

## What you must know before using it (read this)

| Metric / capability | Source | Needs |
|---|---|---|
| New post detection (text, photo, video, albums, forwards, edits) | Bot API webhook | Bot is **administrator** of the channel |
| Reaction counts per emoji | Bot API `message_reaction_count` updates | Bot is administrator; counts only for events after the bot was added |
| Subscriber count | Bot API `getChatMemberCount` | Bot in channel |
| Reacting to a post (one identity: your bot) | Bot API `setMessageReaction` | Bot in channel, emoji allowed by the channel |
| **Views, forwards, replies** | **MTProto** (`getMessages`), read-only, your own `api_id` | A Telegram account that is a member of the channel |
| Reading an existing post by URL (text, date, old stats) | **MTProto** | same |

The Bot API has **no view counter, no forward counter and no method to read an existing message**. Without MTProto configured, those values display `—` / `UNAVAILABLE`. They are never estimated. Averages shown in Analytics are labelled `CALCULATED` (computed from stored snapshots); Telegram values are labelled `TELEGRAM`.

## Quick start (local, development)

```bash
cp .env.example .env            # set DATABASE_URL, REDIS_URL, ENCRYPTION_KEY (openssl rand -hex 32)
npm install
npm run migrate
ADMIN_EMAIL=you@x.com ADMIN_PASSWORD='a-long-passphrase' npm run user:create
npm run worker &                # webhook + queues
npm run dev                     # dashboard on :3000
```

Telegram only delivers webhooks to public HTTPS: for local work use a tunnel and set `PUBLIC_BASE_URL` to it before saving the bot token in **Settings**.

## Production

See [docs/DEPLOY.md](docs/DEPLOY.md). Short version: `cp .env.example .env`, fill it, `docker compose up -d --build`, create the admin, open `https://your.domain`, add the bot token in Settings.

## Tests

```bash
npm test          # 45 tests: URL parser, crypto, passwords, and the full pipeline
npm run typecheck
```

The integration suite starts the real worker against real Postgres + Redis with a local Bot API double. It covers: webhook auth, duplicate deliveries, albums, edits, forwarded posts, reaction counts, notification + reaction jobs, 5xx retry, 429 `retry_after`, permanent failures, auto-pause, crash recovery of unprocessed events, snapshot scheduling, Mode B registration and retention.

## Verified vs not verified

Verified in this repository: everything above, plus a Playwright run of the dashboard (login, lockout of unauthenticated access, bot + channel setup, automation form, live webhooks → posts/jobs, post lookup by URL, mobile layout without horizontal scroll, no console errors), a production build, and the worker bundle running from a clean `npm ci --omit=dev`.

**Not verified** (no credentials / no Docker daemon in the build environment):
- Real calls to `api.telegram.org` (the Bot API client is tested against a local double that follows the documented request/response shapes).
- The MTProto adapter (`src/lib/telegram/mtproto.ts`) against Telegram. It is thin and isolated, but treat the first real run as a test: check **Activity Logs** after the first poll.
- `docker compose build/up` (the compose file validates; the image steps were reproduced by hand).
- Let's Encrypt issuance by Caddy (needs your DNS).
