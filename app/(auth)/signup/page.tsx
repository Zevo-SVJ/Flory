import type { Metadata } from 'next'
import Link from 'next/link'
import { AuthShell, AuthDivider } from '@/components/auth/auth-shell'
import { CredentialsForm } from '@/components/auth/auth-form'
import { GoogleButton } from '@/components/auth/google-button'
import { signUp } from '@/lib/auth/actions'
import { safeNext, loginWithNext } from '@/lib/auth/redirects'
import { readPendingInput } from '@/lib/auth/pending-input'

export const metadata: Metadata = {
  title: 'Create your Worth profile',
  robots: { index: false },
}

export default async function SignupPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>
}) {
  const { next: rawNext } = await searchParams
  const next = safeNext(rawNext)

  // Show the visitor the link they pasted, so they can see it wasn't lost.
  const fromNext = /[?&]url=([^&]+)/.exec(next)?.[1]
  const pendingUrl = fromNext ? decodeURIComponent(fromNext) : await readPendingInput()

  return (
    <AuthShell
      title="Create your Worth profile."
      subtitle="Save your analyses and personalise how Worth helps you decide."
      pendingUrl={pendingUrl}
      footer={
        <>
          Already have an account?{' '}
          <Link
            href={loginWithNext(next)}
            className="text-ink font-medium underline underline-offset-4"
          >
            Sign in
          </Link>
        </>
      }
    >
      <div className="flex flex-col gap-5">
        <GoogleButton next={next} />
        <AuthDivider />
        <CredentialsForm
          action={signUp}
          next={next}
          submitLabel="Continue with email"
          pendingLabel="Creating your profile…"
          passwordHint="At least 8 characters."
          autoComplete="new-password"
        />
      </div>
    </AuthShell>
  )
}
