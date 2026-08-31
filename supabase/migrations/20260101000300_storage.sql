-- ===========================================================================
-- Worth — screenshot storage
--
-- Private bucket. Objects live at `{user_id}/{uuid}.{ext}` and policies scope
-- every operation to the first path segment matching the caller's UID, so one
-- user can never read, overwrite or delete another user's upload.
--
-- Uploaded screenshots are never public.
-- ===========================================================================

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'analysis-uploads',
  'analysis-uploads',
  false,
  8388608, -- 8 MB, matching MAX_UPLOAD_BYTES in lib/analysis/validate.ts
  array['image/png', 'image/jpeg', 'image/webp', 'image/heic', 'image/heif']
)
on conflict (id) do update
  set public             = excluded.public,
      file_size_limit    = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

-- Policies are defined on storage.objects, which Supabase manages. We only add
-- our own named policies here — the table's own RLS is already enabled.
drop policy if exists "uploads_select_own" on storage.objects;
create policy "uploads_select_own"
  on storage.objects for select
  to authenticated
  using (
    bucket_id = 'analysis-uploads'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

drop policy if exists "uploads_insert_own" on storage.objects;
create policy "uploads_insert_own"
  on storage.objects for insert
  to authenticated
  with check (
    bucket_id = 'analysis-uploads'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

drop policy if exists "uploads_delete_own" on storage.objects;
create policy "uploads_delete_own"
  on storage.objects for delete
  to authenticated
  using (
    bucket_id = 'analysis-uploads'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );
