/**
 * Redirect-target validation.
 *
 * Every auth entry point accepts a `next` parameter so a submitted URL survives
 * sign-up. That parameter is attacker-controllable, so it is validated here
 * before it is ever used in a redirect — an unchecked `next` is an open
 * redirect, which is exactly how phishing links get laundered through a
 * trusted domain.
 */

export const DEFAULT_REDIRECT = '/dashboard'

/** Paths a signed-in user must never be bounced back to. */
const DISALLOWED_PREFIXES = ['/login', '/signup', '/forgot-password', '/reset-password', '/auth/']

export function safeNext(
  next: string | null | undefined,
  fallback: string = DEFAULT_REDIRECT,
): string {
  if (!next) return fallback

  // Must be a site-relative path. Rejects "https://evil.com",
  // "//evil.com" (protocol-relative) and "javascript:alert(1)".
  if (!next.startsWith('/')) return fallback
  if (next.startsWith('//')) return fallback
  if (next.includes('\\')) return fallback

  // Backstop: resolve against a dummy origin and confirm nothing escaped.
  let resolved: URL
  try {
    resolved = new URL(next, 'https://worth.invalid')
  } catch {
    return fallback
  }
  if (resolved.origin !== 'https://worth.invalid') return fallback

  if (DISALLOWED_PREFIXES.some((prefix) => resolved.pathname.startsWith(prefix))) {
    return fallback
  }

  return resolved.pathname + resolved.search
}

/** Builds the sign-up link that preserves where the visitor was heading. */
export function signupWithNext(next: string): string {
  return `/signup?next=${encodeURIComponent(next)}`
}

export function loginWithNext(next: string): string {
  return `/login?next=${encodeURIComponent(next)}`
}
