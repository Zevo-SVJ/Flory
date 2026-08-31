import type { Metadata } from 'next'
import { AnalysisRow } from '@/components/app/analysis-row'
import { Card } from '@/components/ui/card'
import { ButtonLink } from '@/components/ui/button'
import { listAnalyses } from '@/lib/analysis/service'

export const metadata: Metadata = { title: 'History', robots: { index: false } }

export default async function HistoryPage() {
  const analyses = await listAnalyses()

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-title text-ink font-serif font-medium">History</h1>
        <p className="text-lead text-muted mt-2">Everything you’ve asked Worth about.</p>
      </div>

      {analyses.length === 0 ? (
        <Card className="flex flex-col items-start gap-3 p-6">
          <p className="text-ink font-medium">Your analyses will appear here.</p>
          <p className="text-muted text-[0.9375rem] leading-snug">
            Nothing yet — paste something you’re thinking about buying and it’ll show up on this
            page.
          </p>
          <ButtonLink href="/analyze" className="mt-1">
            Analyze something
          </ButtonLink>
        </Card>
      ) : (
        <ul className="flex flex-col gap-2">
          {analyses.map((analysis) => (
            <AnalysisRow key={analysis.id} analysis={analysis} />
          ))}
        </ul>
      )}
    </div>
  )
}
