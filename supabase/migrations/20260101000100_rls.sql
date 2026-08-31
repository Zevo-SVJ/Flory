-- ===========================================================================
-- Worth — Row Level Security
--
-- RLS is both ENABLED and FORCED, so it applies even to the table owner.
-- Policies are written per command rather than as a single `for all`, so an
-- over-permissive UPDATE can never silently grant INSERT.
--
-- RLS is never disabled for development convenience.
-- ===========================================================================

alter table public.profiles          enable row level security;
alter table public.profiles          force  row level security;
alter table public.user_preferences  enable row level security;
alter table public.user_preferences  force  row level security;
alter table public.analyses          enable row level security;
alter table public.analyses          force  row level security;

-- ---------------------------------------------------------------------------
-- profiles — a user sees and edits only their own profile.
-- No INSERT policy: rows are created by the sign-up trigger, not by clients.
-- No DELETE policy: profiles are removed by cascade when the auth user is.
-- ---------------------------------------------------------------------------
drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own"
  on public.profiles for select
  to authenticated
  using ((select auth.uid()) = id);

drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own"
  on public.profiles for update
  to authenticated
  using ((select auth.uid()) = id)
  with check ((select auth.uid()) = id);

-- ---------------------------------------------------------------------------
-- user_preferences
-- ---------------------------------------------------------------------------
drop policy if exists "preferences_select_own" on public.user_preferences;
create policy "preferences_select_own"
  on public.user_preferences for select
  to authenticated
  using ((select auth.uid()) = user_id);

drop policy if exists "preferences_insert_own" on public.user_preferences;
create policy "preferences_insert_own"
  on public.user_preferences for insert
  to authenticated
  with check ((select auth.uid()) = user_id);

drop policy if exists "preferences_update_own" on public.user_preferences;
create policy "preferences_update_own"
  on public.user_preferences for update
  to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

-- ---------------------------------------------------------------------------
-- analyses
--
-- NOTE: there is deliberately NO policy granting `anon` any access. A public
-- share link must not be able to expose the submitted URL, the uploaded
-- screenshot path, the raw evidence or the owner. Public reads go through
-- public.get_public_analysis() below, which returns shareable columns only.
-- ---------------------------------------------------------------------------
drop policy if exists "analyses_select_own" on public.analyses;
create policy "analyses_select_own"
  on public.analyses for select
  to authenticated
  using ((select auth.uid()) = user_id);

drop policy if exists "analyses_insert_own" on public.analyses;
create policy "analyses_insert_own"
  on public.analyses for insert
  to authenticated
  with check ((select auth.uid()) = user_id);

drop policy if exists "analyses_update_own" on public.analyses;
create policy "analyses_update_own"
  on public.analyses for update
  to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

drop policy if exists "analyses_delete_own" on public.analyses;
create policy "analyses_delete_own"
  on public.analyses for delete
  to authenticated
  using ((select auth.uid()) = user_id);
