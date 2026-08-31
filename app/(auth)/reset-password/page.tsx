import type { Metadata } from 'next'
import Link from 'next/link'
import { redirect } from 'next/navigation'
import { AuthShell } from '@/components/auth/auth-shell'
import { NewPasswordForm } from '@/components/auth/auth-form'
import { updatePassword } from '@/lib/auth/actions'
import { getCurrentUser } from '@/lib/supabase/server'

export const metadata: Metadata = {
  title: 'Choose a new password',
  robots: { index: false },
}

/**
 * Reached from a recovery email, which establishes a session first. Without one
 * there is nothing to update, so send the visitor back to request a new link.
 */
export default async function ResetPasswordPage() {
  const user = await getCurrentUser()
  if (!user) redirect('/forgot-password')

  return (
    <AuthShell
      title="Choose a new password."
      subtitle="You’ll be signed in once it’s saved."
      footer={
        <Link href="/login" className="text-ink font-medium underline underline-offset-4">
          Back to sign in
        </Link>
      }
    >
      <NewPasswordForm action={updatePassword} />
    </AuthShell>
  )
}
