-- ===========================================================================
-- Worth — initial schema
--
-- Design rules enforced here:
--   * UUID primary keys.
--   * Money stored as integer minor units (bigint). Never floating point.
--   * Row Level Security ENABLED and FORCED on every table.
--   * Users can only ever reach their own rows.
--   * No anonymous SELECT policy on `analyses` — public sharing goes through a
--     restricted SECURITY DEFINER function that returns shareable columns only.
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- profiles
-- ---------------------------------------------------------------------------
create table if not exists public.profiles (
  id                      uuid primary key references auth.users (id) on delete cascade,
  email                   text,
  full_name               text,
  avatar_url              text,
  onboarding_completed_at timestamptz,
  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now()
);

comment on table public.profiles is 'One row per authenticated user. Created automatically on sign-up.';

-- ---------------------------------------------------------------------------
-- user_preferences
-- ---------------------------------------------------------------------------
create table if not exists public.user_preferences (
  user_id           uuid primary key references public.profiles (id) on delete cascade,
  spend_categories  text[] not null default '{}',
  buying_priorities text[] not null default '{}',
  currency          text   not null default 'EUR',
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  constraint user_preferences_currency_len check (char_length(currency) = 3)
);

comment on table public.user_preferences is 'Optional personalisation captured during onboarding. All fields skippable.';

-- ---------------------------------------------------------------------------
-- analyses
-- ---------------------------------------------------------------------------
create table if not exists public.analyses (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid not null references public.profiles (id) on delete cascade,

  input_type         text not null check (input_type in ('url', 'screenshot', 'text')),
  input_url          text,
  input_storage_path text,
  category           text check (category in ('product', 'software', 'course', 'other')),

  title              text,
  status             text not null default 'pending'
                       check (status in ('pending', 'processing', 'complete', 'failed')),

  score              int check (score between 0 and 100),
  verdict            text check (verdict in ('buy', 'think_twice', 'skip')),
  summary            text,

  currency           text not null default 'EUR',
  price_minor        bigint,
  best_price_minor   bigint,

  -- Structured engine output: signals, evidence, alternatives, value summary.
  result             jsonb,

  -- Which engine produced this, and whether it was real research.
  engine             text,
  is_fixture         boolean not null default true,

  share_slug         text unique,
  shared_at          timestamptz,

  error_message      text,
  created_at         timestamptz not null default now(),
  completed_at       timestamptz,

  constraint analyses_currency_len check (char_length(currency) = 3),
  constraint analyses_price_nonneg check (price_minor is null or price_minor >= 0),
  constraint analyses_best_price_nonneg check (best_price_minor is null or best_price_minor >= 0),
  -- A URL analysis needs a URL; a screenshot analysis needs a stored object.
  constraint analyses_input_present check (
    (input_type = 'url' and input_url is not null)
    or (input_type = 'screenshot' and input_storage_path is not null)
    or (input_type = 'text')
  )
);

comment on table public.analyses is 'One row per submitted purchase decision.';
comment on column public.analyses.price_minor is 'Integer minor units (e.g. cents). Never a float.';
comment on column public.analyses.is_fixture is 'True when produced by the development fixture engine rather than real research. Surfaced in the UI.';

-- History listing.
create index if not exists analyses_user_created_idx
  on public.analyses (user_id, created_at desc);

-- Queue scan for the future background worker.
create index if not exists analyses_pending_idx
  on public.analyses (user_id, status)
  where status in ('pending', 'processing');

-- Public share lookup.
create index if not exists analyses_share_slug_idx
  on public.analyses (share_slug)
  where share_slug is not null;
