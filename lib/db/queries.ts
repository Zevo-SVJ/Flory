import 'server-only'

import { createClient } from '@/lib/supabase/server'

/** Reads scoped to the current user. RLS enforces that at the database. */

export async function getProfile() {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) return null

  const { data } = await supabase.from('profiles').select('*').eq('id', user.id).maybeSingle()
  return data
}

export async function getPreferences() {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) return null

  const { data } = await supabase
    .from('user_preferences')
    .select('*')
    .eq('user_id', user.id)
    .maybeSingle()
  return data
}

export async function hasCompletedOnboarding(): Promise<boolean> {
  const profile = await getProfile()
  return Boolean(profile?.onboarding_completed_at)
}
