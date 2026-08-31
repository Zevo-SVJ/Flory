import type { Metadata } from 'next'
import Link from 'next/link'
import { AuthShell } from '@/components/auth/auth-shell'
import { EmailOnlyForm } from '@/components/auth/auth-form'
import { requestPasswordReset } from '@/lib/auth/actions'

export const metadata: Metadata = {
  title: 'Reset your password',
  robots: { index: false },
}

export default function ForgotPasswordPage() {
  return (
    <AuthShell
      title="Reset your password."
      subtitle="We’ll email you a link to set a new one."
      footer={
        <Link href="/login" className="text-ink font-medium underline underline-offset-4">
          Back to sign in
        </Link>
      }
    >
      <EmailOnlyForm
        action={requestPasswordReset}
        submitLabel="Send reset link"
        pendingLabel="Sending…"
      />
    </AuthShell>
  )
}
