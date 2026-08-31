import { NextResponse, type NextRequest } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { safeNext } from '@/lib/auth/redirects'

/**
 * OAuth callback.
 *
 * Exchanges the provider code for a session, then continues to wherever the
 * visitor was heading — including an /analyze URL they pasted before they had
 * an account.
 *
 * The redirect origin comes from the forwarded host rather than the raw request
 * host so this is correct behind a proxy or load balancer.
 */
export async function GET(request: NextRequest) {
  const { searchParams, origin } = request.nextUrl
  const code = searchParams.get('code')
  const next = safeNext(searchParams.get('next'))

  const forwardedHost = request.headers.get('x-forwarded-host')
  const forwardedProto = request.headers.get('x-forwarded-proto') ?? 'https'
  const base =
    process.env.NODE_ENV === 'development' || !forwardedHost
      ? origin
      : `${forwardedProto}://${forwardedHost}`

  if (!code) {
    return NextResponse.redirect(`${base}/login?error=missing_code`)
  }

  const supabase = await createClient()
  const { error } = await supabase.auth.exchangeCodeForSession(code)

  if (error) {
    return NextResponse.redirect(`${base}/login?error=auth_failed`)
  }

  return NextResponse.redirect(`${base}${next}`)
}
