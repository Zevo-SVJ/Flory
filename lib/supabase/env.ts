/**
 * Supabase environment access.
 *
 * Reads are lazy and never happen at module scope, so `next build` succeeds on
 * a fresh clone with an empty `.env` — the usual reason a Supabase app fails
 * its first deploy.
 */

export type SupabaseEnv = { url: string; anonKey: string }

export function readSupabaseEnv(): SupabaseEnv | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  if (!url || !anonKey) return null
  return { url, anonKey }
}

export function requireSupabaseEnv(): SupabaseEnv {
  const env = readSupabaseEnv()
  if (!env) {
    throw new Error(
      'Supabase is not configured. Set NEXT_PUBLIC_SUPABASE_URL and ' +
        'NEXT_PUBLIC_SUPABASE_ANON_KEY in .env.local — see .env.example.',
    )
  }
  return env
}

/** True when Supabase credentials are present. */
export function isSupabaseConfigured(): boolean {
  return readSupabaseEnv() !== null
}

/**
 * The public origin of this deployment, used for OAuth redirects, canonical
 * URLs and the sitemap. Falls back to the Vercel-provided host so preview
 * deployments configure themselves.
 */
export function siteUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_SITE_URL
  if (explicit) return explicit.replace(/\/$/, '')
  const vercel = process.env.VERCEL_URL
  if (vercel) return `https://${vercel}`
  return 'http://localhost:3000'
}
