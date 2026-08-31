import type { Metadata } from 'next'
import Link from 'next/link'
import { AuthShell, AuthDivider } from '@/components/auth/auth-shell'
import { CredentialsForm } from '@/components/auth/auth-form'
import { GoogleButton } from '@/components/auth/google-button'
import { signIn } from '@/lib/auth/actions'
import { safeNext, signupWithNext } from '@/lib/auth/redirects'
import { readPendingInput } from '@/lib/auth/pending-input'

export const metadata: Metadata = {
  title: 'Sign in',
  robots: { index: false },
}

const ERRORS: Record<string, string> = {
  auth_failed: 'That sign-in didn’t complete. Please try again.',
  missing_code: 'That sign-in link was incomplete. Please try again.',
  invalid_link: 'That link isn’t valid. Request a new one.',
  expired_link: 'That link has expired. Request a new one.',
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string; error?: string }>
}) {
  const { next: rawNext, error } = await searchParams
  const next = safeNext(rawNext)

  const fromNext = /[?&]url=([^&]+)/.exec(next)?.[1]
  const pendingUrl = fromNext ? decodeURIComponent(fromNext) : await readPendingInput()

  return (
    <AuthShell
      title="Welcome back."
      subtitle="Sign in to pick up where you left off."
      pendingUrl={pendingUrl}
      footer={
        <>
          New to Worth?{' '}
          <Link
            href={signupWithNext(next)}
            className="text-ink font-medium underline underline-offset-4"
          >
            Create a profile
          </Link>
        </>
      }
    >
      <div className="flex flex-col gap-5">
        {error && ERRORS[error] && (
          <p
            role="alert"
            className="rounded-input border-skip/25 bg-skip-wash text-skip border px-3.5 py-3 text-[0.875rem] font-medium"
          >
            {ERRORS[error]}
          </p>
        )}

        <GoogleButton next={next} />
        <AuthDivider />
        <CredentialsForm
          action={signIn}
          next={next}
          submitLabel="Continue with email"
          pendingLabel="Signing in…"
          autoComplete="current-password"
        />

        <p className="text-center text-[0.875rem]">
          <Link
            href="/forgot-password"
            className="text-graphite hover:text-ink inline-flex min-h-11 items-center underline underline-offset-4"
          >
            Forgot your password?
          </Link>
        </p>
      </div>
    </AuthShell>
  )
}
