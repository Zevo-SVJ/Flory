'use server'

import { redirect } from 'next/navigation'
import { revalidatePath } from 'next/cache'
import { getCurrentUser } from '@/lib/supabase/server'
import { signupWithNext } from '@/lib/auth/redirects'
import { setPendingInput, clearPendingInput } from '@/lib/auth/pending-input'
import { createAnalysis, shareAnalysis } from './service'
import { validateUrl, isCategory } from './validate'

/**
 * Submitting something to analyse.
 *
 * If the visitor isn't signed in, the URL is preserved twice over — in the
 * `next` parameter and in a short-lived cookie — so it is still waiting after
 * sign-up. They never paste it twice.
 */
export async function submitUrl(formData: FormData): Promise<{ error: string } | never> {
  const raw = formData.get('url')?.toString() ?? ''
  const categoryRaw = formData.get('category')?.toString()
  const category = isCategory(categoryRaw) ? categoryRaw : null

  const validation = validateUrl(raw)
  if (!validation.ok) return { error: validation.error }

  const user = await getCurrentUser()
  if (!user) {
    await setPendingInput(validation.url)
    redirect(signupWithNext(`/analyze?url=${encodeURIComponent(validation.url)}`))
  }

  const result = await createAnalysis(user.id, {
    type: 'url',
    url: validation.url,
    category,
  })

  if (!result.ok) return { error: result.error }

  await clearPendingInput()
  revalidatePath('/history')
  redirect(`/analyze/${result.id}`)
}

/**
 * Void-returning wrapper for a plain HTML form submission (no JavaScript).
 * Errors come back as a query parameter, since there is no client state to
 * render them into.
 */
export async function submitUrlForm(formData: FormData): Promise<void> {
  const result = await submitUrl(formData)
  if (result?.error) {
    const url = formData.get('url')?.toString() ?? ''
    redirect(`/analyze?error=${encodeURIComponent(result.error)}&url=${encodeURIComponent(url)}`)
  }
}

/** Creates an analysis from an already-uploaded screenshot. */
export async function submitScreenshot(storagePath: string): Promise<{ error: string } | never> {
  const user = await getCurrentUser()
  if (!user) redirect(signupWithNext('/analyze?input=screenshot'))

  // The path must live in the caller's own folder. Storage RLS enforces this
  // too, but rejecting it here avoids writing a row that points nowhere.
  if (!storagePath.startsWith(`${user.id}/`)) {
    return { error: 'That upload could not be verified. Please try again.' }
  }

  const result = await createAnalysis(user.id, {
    type: 'screenshot',
    storagePath,
    category: null,
  })

  if (!result.ok) return { error: result.error }

  revalidatePath('/history')
  redirect(`/analyze/${result.id}`)
}

/** Creates a public share link for an analysis the caller owns. */
export async function createShareLink(id: string): Promise<{ slug: string } | { error: string }> {
  const user = await getCurrentUser()
  if (!user) return { error: 'Sign in to share this result.' }

  const slug = await shareAnalysis(id)
  if (!slug) return { error: 'That result can’t be shared yet.' }

  revalidatePath(`/analyze/${id}`)
  return { slug }
}
