'use client'

import { createBrowserClient } from '@supabase/ssr'
import type { Database } from '@/types/database'
import { requireSupabaseEnv } from './env'

/**
 * Browser Supabase client.
 *
 * Used only where a client component genuinely needs it: starting the Google
 * OAuth redirect and uploading a screenshot. Sessions live in cookies, handled
 * by @supabase/ssr — Worth never writes auth tokens to localStorage.
 */
export function createClient() {
  const { url, anonKey } = requireSupabaseEnv()
  return createBrowserClient<Database>(url, anonKey)
}
