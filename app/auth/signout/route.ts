import { NextResponse, type NextRequest } from 'next/server'
import { createClient } from '@/lib/supabase/server'

/**
 * Sign out.
 *
 * POST only, so it cannot be triggered by a link prefetch, an <img> tag or a
 * crawler following a URL.
 */
export async function POST(request: NextRequest) {
  const supabase = await createClient()
  await supabase.auth.signOut()
  return NextResponse.redirect(new URL('/', request.nextUrl.origin), { status: 303 })
}
