'use client'

import { useActionState } from 'react'
import { useFormStatus } from 'react-dom'
import type { AuthState } from '@/lib/auth/actions'
import { Field, Input } from '@/components/ui/field'
import { Button } from '@/components/ui/button'

type Action = (state: AuthState, formData: FormData) => Promise<AuthState>

const EMPTY: AuthState = { error: null }

function SubmitButton({ label, pendingLabel }: { label: string; pendingLabel: string }) {
  const { pending } = useFormStatus()
  return (
    <Button type="submit" size="lg" disabled={pending} className="w-full">
      {pending ? pendingLabel : label}
    </Button>
  )
}

/** Email + password. Errors render inline and the email is preserved. */
export function CredentialsForm({
  action,
  next,
  submitLabel,
  pendingLabel,
  passwordHint,
  autoComplete,
}: {
  action: Action
  next: string
  submitLabel: string
  pendingLabel: string
  passwordHint?: string
  autoComplete: 'current-password' | 'new-password'
}) {
  const [state, formAction] = useActionState(action, EMPTY)

  if (state.sent) {
    return <CheckInbox email={state.email} />
  }

  return (
    <form action={formAction} className="flex flex-col gap-4">
      <input type="hidden" name="next" value={next} />

      <Field label="Email" htmlFor="email">
        <Input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          inputMode="email"
          autoCapitalize="none"
          required
          defaultValue={state.email}
          placeholder="you@example.com"
        />
      </Field>

      <Field label="Password" htmlFor="password" hint={passwordHint}>
        <Input
          id="password"
          name="password"
          type="password"
          autoComplete={autoComplete}
          required
          minLength={8}
          placeholder="••••••••"
        />
      </Field>

      {state.error && (
        <p role="alert" className="text-skip text-[0.875rem] font-medium">
          {state.error}
        </p>
      )}

      <SubmitButton label={submitLabel} pendingLabel={pendingLabel} />
    </form>
  )
}

/** Email-only form, used for password recovery. */
export function EmailOnlyForm({
  action,
  submitLabel,
  pendingLabel,
}: {
  action: Action
  submitLabel: string
  pendingLabel: string
}) {
  const [state, formAction] = useActionState(action, EMPTY)

  if (state.sent) {
    return <CheckInbox email={state.email} />
  }

  return (
    <form action={formAction} className="flex flex-col gap-4">
      <Field label="Email" htmlFor="email">
        <Input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          inputMode="email"
          autoCapitalize="none"
          required
          defaultValue={state.email}
          placeholder="you@example.com"
        />
      </Field>

      {state.error && (
        <p role="alert" className="text-skip text-[0.875rem] font-medium">
          {state.error}
        </p>
      )}

      <SubmitButton label={submitLabel} pendingLabel={pendingLabel} />
    </form>
  )
}

/** New-password form used after a recovery link. */
export function NewPasswordForm({ action }: { action: Action }) {
  const [state, formAction] = useActionState(action, EMPTY)

  return (
    <form action={formAction} className="flex flex-col gap-4">
      <Field label="New password" htmlFor="password" hint="At least 8 characters.">
        <Input
          id="password"
          name="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          placeholder="••••••••"
        />
      </Field>

      {state.error && (
        <p role="alert" className="text-skip text-[0.875rem] font-medium">
          {state.error}
        </p>
      )}

      <SubmitButton label="Save new password" pendingLabel="Saving…" />
    </form>
  )
}

function CheckInbox({ email }: { email?: string }) {
  return (
    <div className="rounded-object border-line bg-surface border p-5">
      <h2 className="text-ink text-[0.9375rem] font-semibold">Check your inbox</h2>
      <p className="text-graphite mt-2 text-[0.875rem] leading-relaxed">
        If {email ? <span className="text-ink">{email}</span> : 'that address'} has an account with
        us, there’s a link on its way. Open it on this device to continue.
      </p>
    </div>
  )
}
