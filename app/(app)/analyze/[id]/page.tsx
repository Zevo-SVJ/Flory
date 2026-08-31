import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { getAnalysis } from '@/lib/analysis/service'
import { VerdictCard } from '@/components/worth/verdict-card'
import { FixtureNotice } from '@/components/worth/fixture-notice'
import { EvidenceList } from '@/components/worth/evidence-list'
import { AlternativesList } from '@/components/worth/alternatives-list'
import { ShareResult } from '@/components/app/share-result'
import { AnalysisProgress } from '@/components/app/analysis-progress'
import { Card } from '@/components/ui/card'
import { displayUrl } from '@/lib/analysis/format'

export const metadata: Metadata = { title: 'Result', robots: { index: false } }

export default async function ResultPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const analysis = await getAnalysis(id)

  if (!analysis) notFound()

  if (analysis.status === 'pending' || analysis.status === 'processing') {
    return <AnalysisProgress />
  }

  if (analysis.status === 'failed') {
    return (
      <div className="flex flex-col gap-5">
        <Card className="p-6">
          <h1 className="text-heading text-ink font-serif font-medium">
            Worth couldn’t finish this one.
          </h1>
          <p className="text-muted mt-2 text-[0.9375rem] leading-relaxed">
            {analysis.errorMessage ?? 'Something went wrong during the analysis.'}
          </p>
          <Link
            href="/analyze"
            className="text-ink mt-5 inline-flex min-h-11 items-center font-medium underline underline-offset-4"
          >
            Try again
          </Link>
        </Card>
      </div>
    )
  }

  const evidence = analysis.result?.evidence ?? []
  const alternatives = analysis.result?.alternatives ?? []

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link
          href="/history"
          className="text-muted hover:text-ink inline-flex min-h-11 items-center text-[0.875rem] underline underline-offset-4"
        >
          ← All analyses
        </Link>
        {analysis.inputUrl && (
          <p className="text-faint mt-1 truncate text-[0.8125rem]" title={analysis.inputUrl}>
            {displayUrl(analysis.inputUrl, 70)}
          </p>
        )}
      </div>

      {analysis.isFixture && <FixtureNotice />}

      <VerdictCard analysis={analysis} showLabel={false} />

      {analysis.result?.valueSummary && (
        <Card className="p-5">
          <h2 className="text-muted text-[0.6875rem] font-medium tracking-[0.14em] uppercase">
            What you’re getting
          </h2>
          <p className="text-ink-2 mt-2 text-[0.9375rem] leading-relaxed">
            {analysis.result.valueSummary}
          </p>
        </Card>
      )}

      {evidence.length > 0 && <EvidenceList evidence={evidence} />}
      {alternatives.length > 0 && <AlternativesList alternatives={alternatives} />}

      <ShareResult analysis={analysis} />
    </div>
  )
}
