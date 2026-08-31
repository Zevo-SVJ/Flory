import { NextResponse, type NextRequest } from 'next/server'
import type { EmailOtpType } from '@supabase/supabase-js'
import { createClient } from '@/lib/supabase/server'
import { safeNext } from '@/lib/auth/redirects'

/**
 * Email link verification.
 *
 * Handles both sign-up confirmation and password recovery. Recovery links land
 * on /reset-password with an active session so the new password can be set.
 */
export async function GET(request: NextRequest) {
  const { searchParams, origin } = request.nextUrl
  const tokenHash = searchParams.get('token_hash')
  const type = searchParams.get('type') as EmailOtpType | null
  const isRecovery = type === 'recovery'
  const next = safeNext(searchParams.get('next'), isRecovery ? '/reset-password' : '/dashboard')

  if (!tokenHash || !type) {
    return NextResponse.redirect(`${origin}/login?error=invalid_link`)
  }

  const supabase = await createClient()
  const { error } = await supabase.auth.verifyOtp({ type, token_hash: tokenHash })

  if (error) {
    return NextResponse.redirect(`${origin}/login?error=expired_link`)
  }

  return NextResponse.redirect(`${origin}${next}`)
}
