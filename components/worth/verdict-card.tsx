import type { Analysis } from '@/lib/analysis/types'
import { VERDICT_LABEL, VERDICT_STYLE } from '@/lib/analysis/verdict'
import { cn } from '@/lib/utils/cn'
import { Card } from '@/components/ui/card'
import { ScoreDial } from './score-dial'
import { MoneyRow } from './money-delta'
import { SignalList } from './signal-list'
import { FixtureNotice } from './fixture-notice'

/**
 * The Worth result.
 *
 * This single component renders the landing page's illustrative preview, the
 * authenticated result page and the public share page. Fixtures feed it today;
 * the research engine will feed it next. Nothing here changes when that happens.
 *
 * The verdict stays visually dominant — Worth is a decision product, not a
 * research report.
 */
export function VerdictCard({
  analysis,
  showSignals = true,
  showLabel = true,
  className,
}: {
  analysis: Analysis
  showSignals?: boolean
  showLabel?: boolean
  className?: string
}) {
  const { score, verdict, summary, title } = analysis
  if (score === null || verdict === null) return null

  const style = VERDICT_STYLE[verdict]
  const signals = analysis.result?.signals ?? []

  return (
    <Card className={cn('min-w-0 overflow-hidden', className)}>
      {showLabel && (
        <div className="border-rule flex items-center justify-between gap-3 border-b px-4 py-2.5 sm:px-6">
          <FixtureNotice variant="badge" />
          <span className="text-faint text-[0.6875rem] font-semibold tracking-[0.16em] uppercase">
            Worth
          </span>
        </div>
      )}

      <div className="flex flex-col gap-5 p-4 sm:p-6">
        {/* Verdict — the dominant element. */}
        <div className="flex items-center gap-4 sm:gap-6">
          <ScoreDial score={score} verdict={verdict} />
          <div className="min-w-0 flex-1">
            {title && (
              <p className="text-muted mb-1.5 truncate text-[0.8125rem]" title={title}>
                {title}
              </p>
            )}
            <p
              className={cn(
                'text-[1.75rem] leading-none font-semibold tracking-[-0.02em] uppercase sm:text-[2.25rem]',
                style.text,
              )}
            >
              {VERDICT_LABEL[verdict]}
            </p>
            {summary && (
              <p className="text-ink-2 mt-2.5 font-serif text-[1.0625rem] leading-snug sm:text-lg">
                {summary}
              </p>
            )}
          </div>
        </div>

        {analysis.priceMinor !== null && (
          <div className="border-rule border-t pt-4">
            <MoneyRow
              priceMinor={analysis.priceMinor}
              bestPriceMinor={analysis.bestPriceMinor}
              currency={analysis.currency}
            />
          </div>
        )}

        {showSignals && signals.length > 0 && (
          <div className="border-rule border-t pt-1">
            <SignalList signals={signals} />
          </div>
        )}
      </div>
    </Card>
  )
}
