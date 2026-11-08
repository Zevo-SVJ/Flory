# Architecture & decisions

## Processes

```
Telegram ──HTTPS──► Caddy ──► /tg/webhook/<token>  ──► worker :4000 ──► Postgres (webhook_events)
                      │                                   │                │
                      └──► everything else ──► web :3000 ─┤                └► BullMQ (Redis) ► workers
                                                          └── Postgres        updates · actions · stats
```

- **web** (Next.js 16, standalone): dashboard, auth, server actions. Reads Postgres directly. Holds no Telegram token in the browser; it decrypts it server-side only to call Telegram.
- **worker** (Node): the only process Telegram talks to. Receives webhooks, runs BullMQ workers and schedulers. **Independent of the frontend**: web can be down and posts are still captured.
- **Postgres**: source of truth. **Redis (AOF)**: queue transport only; anything lost from Redis is rebuilt from Postgres.

## Why two Telegram APIs

| Need | Bot API | MTProto |
|---|---|---|
| Push of new posts | ✅ webhook `channel_post` | — |
| Reaction counts | ✅ `message_reaction_count` (admin bot) | ✅ `Message.reactions` |
| Views / forwards / replies | ❌ not exposed | ✅ `Message.views/.forwards/.replies` |
| Read an old post by id | ❌ | ✅ `getMessages` |
| Bot reacts | ✅ `setMessageReaction` | — |

MTProto is used **only for reading**, only through documented methods, with your own `api_id`, and never calls `messages.getMessagesViews(increment=true)`, so it does not inflate counters. It is optional: without it the system is fully functional for detection, reactions and reaction analytics.
The adapter uses the `telegram` (GramJS) package, which is archived upstream; it is confined to one file behind the `MtprotoSource` interface so it can be swapped (for example for the maintained fork `teleproto`) without touching anything else.

## Reliability design

1. **Persist, then enqueue.** The webhook handler inserts into `webhook_events` (`update_id UNIQUE` → duplicate deliveries dropped), then enqueues `evt-<id>`. DB down → HTTP 503 so Telegram redelivers. Redis down → event stays `pending`; a sweeper (every 30 s and at boot) re-enqueues it.
2. **Idempotent processing.** Posts are `UNIQUE(channel_id, message_id)`; jobs are `UNIQUE(dedupe_key)` (`reaction:<chat>:m:<id>` or `…:g:<album>`); BullMQ `jobId` equals the row id. Processing an event twice cannot create two posts or two reactions.
3. **Retry with exponential backoff.** Client level: 5xx/network, 3 tries (0.5 s, 1 s). Queue level: BullMQ exponential backoff, attempts per channel setting. `429` → worker-wide `rateLimit(retry_after)`. Permanent errors (400/403, invalid reaction…) fail immediately and are logged.
4. **Failure policy per channel.** `pause_after_failures` N: after N consecutive failures (counted per job kind from history, in the same transaction that settles the job) monitoring pauses automatically and an error is logged.
5. **Resume after restart.** At boot the worker runs migrations, re-enqueues pending events and orphaned jobs, and re-registers schedulers. Redis uses AOF.
6. **DB outage.** `query()` retries transient connection errors with backoff; the pool survives idle-client errors.
7. **Health.** `GET /health` on the worker (DB + Redis), `GET /api/health` on web, Docker healthchecks, `scripts/healthcheck.sh` for an external monitor.

## Statistics engine

- `post_statistics` is append-only: `views/forwards/replies` are `NULL` when the source cannot provide them (a Bot API reaction event writes `views = NULL`, never a copied value).
- `post_reactions` holds the latest count per emoji; an emoji absent from a newer update is removed.
- **Polling cadence** (MTProto only): per channel `monitor_interval_s` (default 900 s, min 60). Posts < 6 h old use ×1, < 48 h ×4, older ×16; tracking stops after `tracking_days` (default 14), except posts registered by URL. A post that Telegram stops returning is marked untracked and logged.
- **Retention** (nightly 03:17 UTC): webhook events and logs by age; snapshots older than `stats_full_days` are reduced to one per day per post.
- **Averages** in Analytics are computed in SQL over posts that have real view data, shown with `CALCULATED`; no extrapolation.

## Reactions

One identity: the configured bot. `setMessageReaction` replaces the bot's reaction, so Telegram itself enforces one reaction per post. Auto-reaction: one job per post (per album: first message). Manual reaction from the post page: one job per (post, emoji). Emoji are validated against Telegram's list and the channel's `available_reactions`. Every action is logged as `bot:@username`. There is deliberately no multi-account path.
Albums: reactions/notifications act once per album, on the first message received. Whether Telegram displays the reaction on the whole album or only that message is not documented; check on your first album.

## Security

- Auth: single-purpose private login, scrypt (N=2^15) hashing, min 12-char passwords, random 256-bit session tokens stored as SHA-256, `HttpOnly; SameSite=Strict; Secure` cookie, 7-day expiry, sign-out-everywhere, password change revokes other sessions.
- Brute force: 5 failures / 15 min per (IP, email), constant-time compare path for unknown users.
- Proxy (`proxy.ts`) blocks cookie-less requests; every page re-validates the session server-side (`requireUser`), every server action does too.
- Secrets: bot token and MTProto session encrypted AES-256-GCM (`ENCRYPTION_KEY`), never serialised to the client. Avatars are proxied through an authenticated route.
- Webhook: path token **and** `X-Telegram-Bot-Api-Secret-Token` header, both constant-time compared; 1 MB body cap.
- Input: zod on every action; URL parser rejects unsupported links; HTML escaped in notifications.
- Postgres and Redis are not published on the host.

## Known limits

- Single admin user by design (private tool). `users` supports more rows, but there is no roles model.
- Without MTProto, an individual post looked up by URL cannot be verified, nor its text/views loaded; the UI says so.
- Reaction updates reach the bot only for activity after it became administrator.
- `message_reaction_count` is batched by Telegram; reaction history resolution is Telegram's, not ours.
