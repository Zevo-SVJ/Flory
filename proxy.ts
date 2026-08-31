import type { NextRequest } from 'next/server'
import { updateSession } from '@/lib/supabase/proxy'

/**
 * Next.js 16 replaced the `middleware.ts` convention with `proxy.ts`.
 * Running `middleware.ts` in Next 16 logs a deprecation warning.
 */
export async function proxy(request: NextRequest) {
  return updateSession(request)
}

export const config = {
  matcher: [
    /*
     * Every path except static assets and image files — auth cookies must be
     * refreshed on real navigations, not on asset requests.
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|avif|ico|woff2?)$).*)',
  ],
}
