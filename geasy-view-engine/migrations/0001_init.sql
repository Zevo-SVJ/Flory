-- GEASY VIEW ENGINE — initial schema
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE users (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email          text NOT NULL,
  password_hash  text NOT NULL,
  created_at     timestamptz NOT NULL DEFAULT now(),
  last_login_at  timestamptz
);
CREATE UNIQUE INDEX users_email_uniq ON users (lower(email));

CREATE TABLE sessions (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash  text NOT NULL UNIQUE,
  created_at  timestamptz NOT NULL DEFAULT now(),
  expires_at  timestamptz NOT NULL,
  ip          text,
  user_agent  text
);
CREATE INDEX sessions_expires_idx ON sessions (expires_at);

CREATE TABLE login_attempts (
  id          bigserial PRIMARY KEY,
  key         text NOT NULL,
  attempted_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX login_attempts_key_idx ON login_attempts (key, attempted_at DESC);

-- Encrypted third-party credentials (bot token, MTProto session). One row per kind.
CREATE TABLE telegram_credentials (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kind           text NOT NULL CHECK (kind IN ('bot', 'mtproto')),
  label          text,
  payload_enc    text NOT NULL,          -- AES-256-GCM, see lib/crypto.ts
  identity       jsonb NOT NULL DEFAULT '{}'::jsonb,  -- non-secret: bot id/username, account name
  webhook_secret text,                   -- bot only: path+header secret (random, not the token)
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX telegram_credentials_kind_uniq ON telegram_credentials (kind);

CREATE TABLE channels (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tg_chat_id       bigint NOT NULL,                 -- e.g. -1001234567890
  username         text,                            -- without @, public channels only
  title            text NOT NULL,
  photo_file_id    text,
  subscriber_count integer,
  subscribers_checked_at timestamptz,
  is_private       boolean NOT NULL DEFAULT false,
  status           text NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending','connected','no_access','disconnected','error')),
  status_detail    text,
  status_changed_at timestamptz NOT NULL DEFAULT now(),
  available_reactions jsonb,                        -- null = all emoji allowed; [] = none
  bot_can_post_reactions boolean,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX channels_chat_uniq ON channels (tg_chat_id);
CREATE INDEX channels_username_idx ON channels (lower(username));

CREATE TABLE automation_settings (
  channel_id          uuid PRIMARY KEY REFERENCES channels(id) ON DELETE CASCADE,
  monitoring_enabled  boolean NOT NULL DEFAULT true,
  stats_enabled       boolean NOT NULL DEFAULT true,
  reaction_enabled    boolean NOT NULL DEFAULT false,
  reaction_emoji      text NOT NULL DEFAULT '👍',
  notify_enabled      boolean NOT NULL DEFAULT false,
  notify_chat_id      bigint,
  monitor_interval_s  integer NOT NULL DEFAULT 900 CHECK (monitor_interval_s BETWEEN 60 AND 86400),
  tracking_days       integer NOT NULL DEFAULT 14  CHECK (tracking_days BETWEEN 1 AND 365),
  max_retries         integer NOT NULL DEFAULT 5   CHECK (max_retries BETWEEN 0 AND 20),
  pause_after_failures integer NOT NULL DEFAULT 0  CHECK (pause_after_failures BETWEEN 0 AND 100), -- 0 = never auto-pause
  consecutive_failures integer NOT NULL DEFAULT 0,
  updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE telegram_posts (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  channel_id       uuid NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
  message_id       bigint NOT NULL,
  source           text NOT NULL CHECK (source IN ('webhook','manual','mtproto')),
  media_type       text NOT NULL DEFAULT 'unknown'
                   CHECK (media_type IN ('text','photo','video','animation','document','audio','voice','poll','other','unknown')),
  media_group_id   text,
  text             text,
  is_forwarded     boolean NOT NULL DEFAULT false,
  forward_origin   jsonb,
  is_edited        boolean NOT NULL DEFAULT false,
  edited_at        timestamptz,
  published_at     timestamptz,
  tracking_enabled boolean NOT NULL DEFAULT true,
  last_stats_at    timestamptz,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (channel_id, message_id)
);
CREATE INDEX telegram_posts_channel_pub_idx ON telegram_posts (channel_id, published_at DESC NULLS LAST);
CREATE INDEX telegram_posts_group_idx ON telegram_posts (channel_id, media_group_id) WHERE media_group_id IS NOT NULL;
CREATE INDEX telegram_posts_tracking_idx ON telegram_posts (channel_id, last_stats_at) WHERE tracking_enabled;

-- Append-only history. views/forwards/replies are NULL when the source cannot provide them.
CREATE TABLE post_statistics (
  id              bigserial PRIMARY KEY,
  post_id         uuid NOT NULL REFERENCES telegram_posts(id) ON DELETE CASCADE,
  captured_at     timestamptz NOT NULL DEFAULT now(),
  source          text NOT NULL CHECK (source IN ('bot_api','mtproto')),
  views           integer,
  forwards        integer,
  replies         integer,
  reactions_total integer,
  reactions       jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX post_statistics_post_time_idx ON post_statistics (post_id, captured_at DESC);
CREATE INDEX post_statistics_time_idx ON post_statistics (captured_at);

-- Latest known reaction count per emoji.
CREATE TABLE post_reactions (
  post_id     uuid NOT NULL REFERENCES telegram_posts(id) ON DELETE CASCADE,
  reaction    text NOT NULL,       -- emoji, or 'custom:<id>' / 'paid'
  count       integer NOT NULL CHECK (count >= 0),
  source      text NOT NULL CHECK (source IN ('bot_api','mtproto')),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (post_id, reaction)
);

CREATE TABLE automation_jobs (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  channel_id    uuid NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
  post_id       uuid REFERENCES telegram_posts(id) ON DELETE CASCADE,
  kind          text NOT NULL CHECK (kind IN ('reaction','notify')),
  payload       jsonb NOT NULL DEFAULT '{}'::jsonb,
  dedupe_key    text NOT NULL UNIQUE,   -- idempotency: one job per (kind, target)
  status        text NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','running','done','failed','skipped')),
  attempts      integer NOT NULL DEFAULT 0,
  last_error    text,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  finished_at   timestamptz
);
CREATE INDEX automation_jobs_status_idx ON automation_jobs (status, created_at DESC);
CREATE INDEX automation_jobs_channel_idx ON automation_jobs (channel_id, created_at DESC);

CREATE TABLE webhook_events (
  id           bigserial PRIMARY KEY,
  update_id    bigint NOT NULL UNIQUE,   -- Telegram update_id: dedupe key
  update_type  text NOT NULL,
  payload      jsonb NOT NULL,
  status       text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processed','ignored','failed')),
  attempts     integer NOT NULL DEFAULT 0,
  error        text,
  received_at  timestamptz NOT NULL DEFAULT now(),
  processed_at timestamptz
);
CREATE INDEX webhook_events_status_idx ON webhook_events (status, received_at);
CREATE INDEX webhook_events_received_idx ON webhook_events (received_at);

CREATE TABLE activity_logs (
  id          bigserial PRIMARY KEY,
  created_at  timestamptz NOT NULL DEFAULT now(),
  level       text NOT NULL CHECK (level IN ('info','warn','error')),
  category    text NOT NULL,        -- channel | webhook | stats | reaction | notify | auth | system
  action      text NOT NULL,
  channel_id  uuid REFERENCES channels(id) ON DELETE SET NULL,
  post_id     uuid REFERENCES telegram_posts(id) ON DELETE SET NULL,
  actor       text NOT NULL DEFAULT 'system',  -- system | user:<email> | bot:@name
  message     text NOT NULL,
  meta        jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX activity_logs_time_idx ON activity_logs (created_at DESC);
CREATE INDEX activity_logs_category_idx ON activity_logs (category, created_at DESC);
CREATE INDEX activity_logs_channel_idx ON activity_logs (channel_id, created_at DESC);

-- Retention (days). Single-row table, editable from Settings.
CREATE TABLE retention_policy (
  id                     boolean PRIMARY KEY DEFAULT true CHECK (id),
  webhook_events_days    integer NOT NULL DEFAULT 14,
  activity_logs_days     integer NOT NULL DEFAULT 90,
  stats_full_days        integer NOT NULL DEFAULT 30,   -- keep every snapshot this long
  stats_downsample_to_daily boolean NOT NULL DEFAULT true -- then keep 1 snapshot/day/post
);
INSERT INTO retention_policy DEFAULT VALUES;

-- Subscriber history per channel (source: Bot API getChatMemberCount).
CREATE TABLE channel_stats (
  id           bigserial PRIMARY KEY,
  channel_id   uuid NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
  captured_at  timestamptz NOT NULL DEFAULT now(),
  subscribers  integer NOT NULL
);
CREATE INDEX channel_stats_idx ON channel_stats (channel_id, captured_at DESC);
