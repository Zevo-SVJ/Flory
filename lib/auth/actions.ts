'use server'

import { redirect } from 'next/navigation'
import { revalidatePath } from 'next/cache'
import { createClient } from '@/lib/supabase/server'
import { siteUrl } from '@/lib/supabase/env'
import { safeNext, DEFAULT_REDIRECT } from './redirects'
import { setPendingInput } from './pending-input'

export type AuthState = { error: string | null; email?: string; sent?: boolean }

/**
 * Auth server actions.
 *
 * Form-first: every one of these is reachable by a plain HTML form submission,
 * so sign-in works before hydration.
 */

function readNext(formData: FormData): string {
  return safeNext(formData.get('next')?.toString())
}

/**
 * Remembers a link the visitor pasted before they had an account, so it
 * survives the round trip through sign-up — including Google OAuth.
 */
async function rememberPendingInput(next: string): Promise<void> {
  const match = /[?&]url=([^&]+)/.exec(next)
  if (!match?.[1]) return
  try {
    await setPendingInput(decodeURIComponent(match[1]))
  } catch {
    /* Cookie write is a convenience; `next` still carries the value. */
  }
}

export async function signIn(_prev: AuthState, formData: FormData): Promise<AuthState> {
  const email = formData.get('email')?.toString().trim() ?? ''
  const password = formData.get('password')?.toString() ?? ''
  const next = readNext(formData)

  if (!email || !password) {
    return { error: 'Enter your email and password.', email }
  }

  const supabase = await createClient()
  const { error } = await supabase.auth.signInWithPassword({ email, password })

  if (error) {
    // Deliberately generic: a specific message would reveal which addresses
    // have accounts.
    return { error: 'That email and password don’t match.', email }
  }

  await rememberPendingInput(next)
  revalidatePath('/', 'layout')
  redirect(next)
}

export async function signUp(_prev: AuthState, formData: FormData): Promise<AuthState> {
  const email = formData.get('email')?.toString().trim() ?? ''
  const password = formData.get('password')?.toString() ?? ''
  const next = readNext(formData)

  if (!email) return { error: 'Enter your email address.', email }
  if (password.length < 8) {
    return { error: 'Use at least 8 characters for your password.', email }
  }

  const supabase = await createClient()
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      emailRedirectTo: `${siteUrl()}/auth/confirm?next=${encodeURIComponent(next)}`,
    },
  })

  if (error) {
    return { error: error.message, email }
  }

  await rememberPendingInput(next)

  // With email confirmation enabled there is no session yet — tell the user to
  // check their inbox rather than silently doing nothing.
  if (!data.session) {
    return { error: null, email, sent: true }
  }

  revalidatePath('/', 'layout')
  redirect(next)
}

export async function requestPasswordReset(
  _prev: AuthState,
  formData: FormData,
): Promise<AuthState> {
  const email = formData.get('email')?.toString().trim() ?? ''
  if (!email) return { error: 'Enter your email address.', email }

  const supabase = await createClient()
  await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: `${siteUrl()}/auth/confirm?next=${encodeURIComponent('/reset-password')}&type=recovery`,
  })

  // Always report success. Reporting whether the address exists would turn this
  // form into an account-enumeration oracle.
  return { error: null, email, sent: true }
}

export async function updatePassword(_prev: AuthState, formData: FormData): Promise<AuthState> {
  const password = formData.get('password')?.toString() ?? ''
  if (password.length < 8) {
    return { error: 'Use at least 8 characters for your password.' }
  }

  const supabase = await createClient()
  const { error } = await supabase.auth.updateUser({ password })
  if (error) return { error: error.message }

  revalidatePath('/', 'layout')
  redirect(DEFAULT_REDIRECT)
}
