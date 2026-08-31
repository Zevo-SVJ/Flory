import type { Metadata } from 'next'
import Link from 'next/link'
import { redirect } from 'next/navigation'
import { AnalyzeInput } from '@/components/worth/analyze-input'
import { Card } from '@/components/ui/card'
import { listAnalyses } from '@/lib/analysis/service'
import { hasCompletedOnboarding } from '@/lib/db/queries'
import { readPendingInput } from '@/lib/auth/pending-input'
import { AnalysisRow } from '@/components/app/analysis-row'

export const metadata: Metadata = { title: 'Dashboard', robots: { index: false } }

export default async function DashboardPage() {
  // A pending link means the user came here to decide something. That beats a
  // personalisation survey, so onboarding waits.
  const pending = await readPendingInput()
  if (pending) redirect(`/analyze?url=${encodeURIComponent(pending)}`)

  if (!(await hasCompletedOnboarding())) redirect('/onboarding')

  const analyses = await listAnalyses(5)

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-page text-ink font-serif font-medium">
          Ready to check your next purchase?
        </h1>
        <p className="text-lead text-graphite mt-2">Paste anything you’re thinking about buying.</p>
        <div className="mt-6">
          <AnalyzeInput size="md" />
        </div>
      </div>

      <section>
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="text-graphite text-[0.6875rem] font-medium tracking-[0.14em] uppercase">
            Recent
          </h2>
          {analyses.length > 0 && (
            <Link
              href="/history"
              className="text-graphite hover:text-ink inline-flex min-h-11 items-center text-[0.875rem] underline underline-offset-4"
            >
              All analyses
            </Link>
          )}
        </div>

        <div className="mt-3">
          {analyses.length === 0 ? (
            <Card className="flex flex-col items-start gap-2 p-6">
              <p className="text-ink font-medium">You haven’t analysed anything yet.</p>
              <p className="text-graphite text-[0.9375rem] leading-snug">
                Paste a product, offer or URL above to get started.
              </p>
            </Card>
          ) : (
            <ul className="flex flex-col gap-2">
              {analyses.map((analysis) => (
                <AnalysisRow key={analysis.id} analysis={analysis} />
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  )
}
