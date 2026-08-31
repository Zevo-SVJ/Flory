'use client'

import { useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import { siteUrl } from '@/lib/supabase/env'

/**
 * Google sign-in.
 *
 * `redirectTo` carries the visitor's intended destination through the provider
 * round trip, so a link pasted before sign-up is still waiting afterwards.
 */
export function GoogleButton({ next }: { next: string }) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleClick() {
    setPending(true)
    setError(null)
    try {
      const supabase = createClient()
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${siteUrl()}/auth/callback?next=${encodeURIComponent(next)}`,
        },
      })
      if (error) {
        setError('Could not start Google sign-in. Try email instead.')
        setPending(false)
      }
    } catch {
      setError('Google sign-in isn’t configured yet. Use email instead.')
      setPending(false)
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={handleClick}
        disabled={pending}
        className="rounded-input border-line-strong bg-surface text-ink hover:border-ink hover:bg-paper-2 inline-flex min-h-12 w-full items-center justify-center gap-2.5 border px-4 font-medium transition disabled:opacity-60 motion-reduce:transition-none"
      >
        <GoogleIcon />
        {pending ? 'Redirecting…' : 'Continue with Google'}
      </button>
      {error && (
        <p role="alert" className="text-skip text-[0.8125rem] font-medium">
          {error}
        </p>
      )}
    </div>
  )
}

function GoogleIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 18 18" aria-hidden>
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62Z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18Z"
      />
      <path
        fill="#FBBC05"
        d="M3.97 10.72a5.4 5.4 0 0 1 0-3.44V4.95H.96a9 9 0 0 0 0 8.1l3.01-2.33Z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.9 11.43 0 9 0A9 9 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58Z"
      />
    </svg>
  )
}
