'use server'

import { redirect } from 'next/navigation'
import { revalidatePath } from 'next/cache'
import { createClient } from '@/lib/supabase/server'
import { safeNext } from './redirects'

export const SPEND_CATEGORIES = [
  'Tech',
  'Fashion',
  'Home',
  'Beauty',
  'Fitness',
  'Software',
  'Courses',
  'Travel',
  'Other',
] as const

export const BUYING_PRIORITIES = [
  'Best price',
  'Best value',
  'Quality',
  'Trust',
  'Durability',
] as const

/**
 * Saves onboarding answers. Both questions are optional — submitting nothing is
 * a valid answer, and "Skip" uses this same action.
 */
export async function saveOnboarding(formData: FormData): Promise<never> {
  const next = safeNext(formData.get('next')?.toString())

  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const categories = formData
    .getAll('spend_categories')
    .map(String)
    .filter((v) => (SPEND_CATEGORIES as readonly string[]).includes(v))

  const priorities = formData
    .getAll('buying_priorities')
    .map(String)
    .filter((v) => (BUYING_PRIORITIES as readonly string[]).includes(v))

  await supabase
    .from('user_preferences')
    .upsert(
      { user_id: user.id, spend_categories: categories, buying_priorities: priorities },
      { onConflict: 'user_id' },
    )

  // Stamped even when skipped, so onboarding never reappears.
  await supabase
    .from('profiles')
    .update({ onboarding_completed_at: new Date().toISOString() })
    .eq('id', user.id)

  revalidatePath('/', 'layout')
  redirect(next)
}
