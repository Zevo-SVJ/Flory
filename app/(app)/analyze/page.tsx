import type { Metadata } from 'next'
import { AnalyzeForm } from '@/components/app/analyze-form'
import { readPendingInput } from '@/lib/auth/pending-input'
import { getCurrentUser } from '@/lib/supabase/server'

export const metadata: Metadata = { title: 'Analyze', robots: { index: false } }

/**
 * The analysis entry point.
 *
 * A URL can arrive three ways, checked in order: the query string, or the
 * pending-input cookie set before sign-up. Either way the visitor never has to
 * paste it twice.
 */
export default async function AnalyzePage({
  searchParams,
}: {
  searchParams: Promise<{ url?: string; input?: string; error?: string }>
}) {
  const { url, input, error } = await searchParams
  const user = await getCurrentUser()
  const prefill = url ?? (await readPendingInput()) ?? ''

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-title text-ink font-serif font-medium">Is it worth your money?</h1>
        <p className="text-lead text-muted mt-2">
          Paste a link, or upload a screenshot of what you’re looking at.
        </p>
      </div>

      <AnalyzeForm
        defaultUrl={prefill}
        userId={user?.id ?? ''}
        openScreenshot={input === 'screenshot'}
        initialError={error}
      />
    </div>
  )
}
