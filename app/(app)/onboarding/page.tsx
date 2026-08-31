import type { Metadata } from 'next'
import { OnboardingForm } from '@/components/app/onboarding-form'
import { getPreferences } from '@/lib/db/queries'
import { safeNext } from '@/lib/auth/redirects'

export const metadata: Metadata = { title: 'Personalise Worth', robots: { index: false } }

export default async function OnboardingPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>
}) {
  const { next: rawNext } = await searchParams
  const next = safeNext(rawNext)
  const preferences = await getPreferences()

  return (
    <OnboardingForm
      next={next}
      initialCategories={preferences?.spend_categories ?? []}
      initialPriorities={preferences?.buying_priorities ?? []}
    />
  )
}
