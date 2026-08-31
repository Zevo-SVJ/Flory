import { cookies } from 'next/headers'
import { createServerClient } from '@supabase/ssr'
import type { Database } from '@/types/database'
import { requireSupabaseEnv } from './env'

/**
 * Server Supabase client, bound to the request's cookie jar.
 *
 * A new client is created per request — never a module-level singleton, which
 * would leak one user's session into another's render.
 *
 * `cookies()` is async in Next.js 16.
 */
export async function createClient() {
  // cookies() is awaited first so Next marks the route dynamic before any
  // configuration error can throw. Without this, a build with no Supabase
  // credentials fails while prerendering instead of deferring to request time.
  const cookieStore = await cookies()
  const { url, anonKey } = requireSupabaseEnv()

  return createServerClient<Database>(url, anonKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll()
      },
      setAll(cookiesToSet) {
        try {
          for (const { name, value, options } of cookiesToSet) {
            cookieStore.set(name, value, options)
          }
        } catch {
          // Called from a Server Component, where cookies are read-only.
          // proxy.ts refreshes the session on every request, so the write is
          // safely redundant here.
        }
      },
    },
  })
}

/**
 * The current user, or null.
 *
 * Always `getUser()`, never `getSession()`, for anything that gates access:
 * the session cookie is user-writable, while `getUser()` revalidates the token
 * against the Supabase auth server.
 */
export async function getCurrentUser() {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  return user
}
