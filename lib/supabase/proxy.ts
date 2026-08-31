import { NextResponse, type NextRequest } from 'next/server'
import { createServerClient } from '@supabase/ssr'
import type { Database } from '@/types/database'
import { readSupabaseEnv } from './env'
import { loginWithNext } from '@/lib/auth/redirects'

/** Routes that require a signed-in user. */
const PROTECTED_PREFIXES = ['/dashboard', '/analyze', '/history', '/settings', '/onboarding']

/** Routes a signed-in user has no reason to see. */
const AUTH_ONLY_PREFIXES = ['/login', '/signup']

function isMatch(pathname: string, prefixes: string[]): boolean {
  return prefixes.some((p) => pathname === p || pathname.startsWith(`${p}/`))
}

/**
 * Refreshes the Supabase session and gates protected routes.
 *
 * This runs before every matched request so a Server Component never renders
 * against an expired token. Note that this is defence in depth, not the
 * authorisation boundary: each protected layout independently re-checks
 * `getUser()`, and Row Level Security is what actually protects the data.
 */
export async function updateSession(request: NextRequest): Promise<NextResponse> {
  let response = NextResponse.next({ request })

  const env = readSupabaseEnv()
  // Without credentials there is no session to refresh. Protected routes render
  // a configuration notice rather than crashing the whole app.
  if (!env) return response

  const supabase = createServerClient<Database>(env.url, env.anonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll()
      },
      setAll(cookiesToSet, headers) {
        for (const { name, value } of cookiesToSet) {
          request.cookies.set(name, value)
        }
        response = NextResponse.next({ request })
        for (const { name, value, options } of cookiesToSet) {
          response.cookies.set(name, value, options)
        }
        // @supabase/ssr supplies the no-store headers that stop a CDN caching
        // one user's refreshed session and serving it to someone else.
        for (const [key, value] of Object.entries(headers)) {
          response.headers.set(key, value)
        }
      },
    },
  })

  // Must be awaited before the response is generated, or a refresh completing
  // later cannot write its cookies.
  const {
    data: { user },
  } = await supabase.auth.getUser()

  const { pathname, search } = request.nextUrl

  if (!user && isMatch(pathname, PROTECTED_PREFIXES)) {
    const url = request.nextUrl.clone()
    const target = loginWithNext(`${pathname}${search}`)
    url.pathname = target.split('?')[0] as string
    url.search = target.includes('?') ? `?${target.split('?')[1]}` : ''
    return NextResponse.redirect(url)
  }

  if (user && isMatch(pathname, AUTH_ONLY_PREFIXES)) {
    const url = request.nextUrl.clone()
    url.pathname = '/dashboard'
    url.search = ''
    return NextResponse.redirect(url)
  }

  return response
}
