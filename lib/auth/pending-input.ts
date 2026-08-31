import { cookies } from 'next/headers'

/**
 * Pending-input preservation.
 *
 * When a signed-out visitor pastes a link and hits Analyze, that link must
 * survive account creation — including the Google OAuth round-trip, which is
 * where these values are normally lost.
 *
 * Two mechanisms cover each other:
 *   1. A validated `next` query parameter (see `lib/auth/redirects.ts`).
 *   2. This short-lived httpOnly cookie, which survives even if the provider
 *      drops state or the confirmation email is opened in a different tab.
 *
 * The user must never have to paste the same link twice.
 */

export const PENDING_INPUT_COOKIE = 'worth_pending_input'

const MAX_AGE_SECONDS = 30 * 60

export async function setPendingInput(url: string): Promise<void> {
  const cookieStore = await cookies()
  cookieStore.set(PENDING_INPUT_COOKIE, url, {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: MAX_AGE_SECONDS,
  })
}

export async function readPendingInput(): Promise<string | null> {
  const cookieStore = await cookies()
  return cookieStore.get(PENDING_INPUT_COOKIE)?.value ?? null
}

export async function clearPendingInput(): Promise<void> {
  const cookieStore = await cookies()
  cookieStore.delete(PENDING_INPUT_COOKIE)
}
