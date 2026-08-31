-- ===========================================================================
-- Worth — triggers and functions
--
-- Every SECURITY DEFINER function here follows the same hardening rules:
--   * set search_path = ''   (no schema-resolution hijacking)
--   * every object fully schema-qualified
--   * EXECUTE revoked from public, then granted only to the roles that need it
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- updated_at maintenance
-- ---------------------------------------------------------------------------
create or replace function public.set_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

drop trigger if exists preferences_set_updated_at on public.user_preferences;
create trigger preferences_set_updated_at
  before update on public.user_preferences
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Profile bootstrap
--
-- Creates the profile and preference rows the moment an auth user is created,
-- so the app never has to handle a signed-in user with no profile row.
--
-- Exceptions are swallowed deliberately: a failure here would otherwise abort
-- the entire sign-up transaction and leave the user unable to register.
-- ---------------------------------------------------------------------------
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, email, full_name, avatar_url)
  values (
    new.id,
    new.email,
    coalesce(
      new.raw_user_meta_data ->> 'full_name',
      new.raw_user_meta_data ->> 'name'
    ),
    new.raw_user_meta_data ->> 'avatar_url'
  )
  on conflict (id) do nothing;

  insert into public.user_preferences (user_id)
  values (new.id)
  on conflict (user_id) do nothing;

  return new;
exception
  when others then
    -- Never block account creation on profile bootstrap.
    raise warning 'handle_new_user failed for %: %', new.id, sqlerrm;
    return new;
end;
$$;

revoke execute on function public.handle_new_user() from public, anon, authenticated;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------------------------------------------------------------------------
-- Public share representation
--
-- The ONLY route by which an unauthenticated visitor can read an analysis.
-- Returns the verdict and the money and nothing else — never input_url,
-- input_storage_path, user_id, evidence sources or the full result payload.
--
-- Only completed, explicitly shared analyses are visible.
-- ---------------------------------------------------------------------------
create or replace function public.get_public_analysis(slug text)
returns table (
  share_slug       text,
  title            text,
  score            int,
  verdict          text,
  summary          text,
  currency         text,
  price_minor      bigint,
  best_price_minor bigint,
  signals          jsonb,
  is_fixture       boolean
)
language sql
stable
security definer
set search_path = ''
as $$
  select
    a.share_slug,
    a.title,
    a.score,
    a.verdict,
    a.summary,
    a.currency,
    a.price_minor,
    a.best_price_minor,
    -- Signals only. Evidence and alternatives stay private.
    coalesce(a.result -> 'signals', '[]'::jsonb) as signals,
    a.is_fixture
  from public.analyses a
  where a.share_slug = get_public_analysis.slug
    and a.share_slug is not null
    and a.status = 'complete'
  limit 1;
$$;

revoke execute on function public.get_public_analysis(text) from public;
grant  execute on function public.get_public_analysis(text) to anon, authenticated;
