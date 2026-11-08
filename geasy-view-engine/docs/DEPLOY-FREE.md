# Free deployment: Supabase + Vercel (no server, no card)

Two free accounts, one project each, three environment variables. The app configures itself on first start (database tables, admin account, scheduler).

**What you get:** automatic post detection (text, photo, video, albums, forwards, edits), reaction counts, bot reactions, notifications, per-channel automation, analytics on reactions and subscribers, history, retention.
**What you do not get:** views and forwards (they need a permanent MTProto connection, impossible on serverless). They show `—`, never an estimate. Use the Docker deployment if you need them.
**Latency:** a post is processed within seconds of Telegram delivering it. If something fails (Telegram error, outage), a scheduler retries every minute with exponential backoff (15 s, 30 s, 1 min… up to 1 h, 8 attempts for events, per-channel max for jobs).

## 1. Supabase (database)
1. supabase.com → sign in with GitHub → **New project**. Pick the region closest to you. **Database password:** letters and digits only (no `@ : / ? #`), 16+ characters. Save it.
2. Wait until the project is ready, then **Database → Extensions**: enable **pg_cron** and **pg_net**.
3. Click **Connect** (top bar) → **Session pooler** → copy the connection string. It looks like `postgresql://postgres.abcd:[YOUR-PASSWORD]@aws-0-eu-west-3.pooler.supabase.com:5432/postgres`. Replace `[YOUR-PASSWORD]` with your password. Use **Session pooler** (port 5432), not “Direct connection” (IPv6 only, unreachable from Vercel) and not “Transaction pooler”.

## 2. Telegram bot
@BotFather → `/newbot` → copy the token.

## 3. Vercel (the site + the webhook)
1. vercel.com → sign in with GitHub → **Add New → Project** → import `Zevo-SVJ/Flory` (grant the Vercel GitHub app access to that repository if asked).
2. **Root Directory:** `geasy-view-engine`. Framework: Next.js (detected).
3. **Environment Variables:**
   | Name | Value |
   |---|---|
   | `DATABASE_URL` | the Session pooler string from step 1 |
   | `ADMIN_EMAIL` | your email |
   | `ADMIN_PASSWORD` | 12+ characters; this becomes your login |
4. **Production branch:** the code lives on `claude/dazzling-ride-rfuf47`. In Project **Settings → Git → Production Branch** set it to that branch (or merge it into `main`), then **Deploy**. A deployment from any other branch gets a protected preview URL that Telegram cannot reach.
5. When the build is green, open `https://<your-project>.vercel.app/login` (wait about 20 s on the very first request: the database is being prepared).

## 4. Connect Telegram
1. Log in → **Settings** → paste the bot token → **Verify and save**. The webhook is registered to your Vercel URL automatically.
2. **Settings → Scheduler** must read *installed* and, within 1–2 minutes, *last tick: just now*. If it says not installed: press **Install scheduler**; if it reports an extension error, enable pg_cron and pg_net (step 1.2).
3. In each channel: Administrators → add your bot (leave optional permissions off if Telegram allows).
4. **My Channels** → paste the channel link → **Connect** → status *Connected*.
5. Publish a test post: it shows in **Overview** within seconds.
6. **Automation** → per channel, enable auto-reaction / notifications as wanted.

## Limits to know
- Vercel Hobby is for personal, non-commercial use; function time limit applies (our work per request is a few hundred milliseconds to a few seconds).
- Supabase free projects pause after 7 days **without any activity**. Telegram posts, the one-minute scheduler and your own visits count as activity, so an active channel keeps it awake; verify in the Supabase dashboard after the first week.
- Secrets: if `ENCRYPTION_KEY` / `CRON_SECRET` are not set, they are derived from `DATABASE_URL`. Changing the database password therefore invalidates the stored bot token: re-enter it in Settings.
- The database connection uses TLS with certificate verification (Supabase root CA bundled). If a connection error mentions a certificate, set `DATABASE_CA_CERT` to the PEM shown in Supabase → Database → Settings → SSL.
