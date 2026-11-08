-- Retry bookkeeping for the serverless (inline) mode + a tiny key/value state table.
ALTER TABLE webhook_events ADD COLUMN last_attempt_at timestamptz;

CREATE TABLE system_state (
  key         text PRIMARY KEY,
  value       jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at  timestamptz NOT NULL DEFAULT now()
);
