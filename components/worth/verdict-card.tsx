import type { Analysis } from '@/lib/analysis/types'
import { VERDICT_LABEL } from '@/lib/analysis/verdict'
import { formatMoney, moneyDelta } from '@/lib/analysis/format'
import { cn } from '@/lib/utils/cn'
import { ScoreMeter } from './score-meter'
import { PriceDrop } from './price-drop'
import { SignalList } from './signal-list'

const VERDICT_TEXT = {
  buy: 'text-buy',
  think_twice: 'text-think',
  skip: 'text-skip',
} as const

/**
 * The Worth result.
 *
 * One component for the authenticated result page and the public share page,
 * built from the same brand objects as the landing page: the banded score
 * meter, the price drop, the signal list. Fixtures feed it today; the research
 * engine will feed it next, and nothing here changes when it does.
 *
 * The verdict stays dominant — Worth is a decision product, not a report.
 */
export function VerdictCard({
  analysis,
  showSignals = true,
  className,
}: {
  analysis: Analysis
  showSignals?: boolean
  className?: string
}) {
  const { score, verdict, summary, title } = analysis
  if (score === null || verdict === null) return null

  const price = formatMoney(analysis.priceMinor, analysis.currency)
  const best = formatMoney(analysis.bestPriceMinor, analysis.currency)
  const delta = moneyDelta(analysis.priceMinor, analysis.bestPriceMinor)
  const saving = delta ? formatMoney(delta.savingMinor, analysis.currency) : null
  const signals = analysis.result?.signals ?? []

  return (
    <div
      className={cn(
        'rounded-object border-line bg-surface min-w-0 overflow-hidden border',
        className,
      )}
    >
      <div className="flex flex-col gap-6 p-5 sm:p-7">
        {title && (
          <div className="flex items-baseline justify-between gap-4">
            <p className="text-ink min-w-0 truncate font-medium" title={title}>
              {title}
            </p>
            {price && <span className="tnum text-ink shrink-0 text-lg font-semibold">{price}</span>}
          </div>
        )}

        <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between sm:gap-8">
          <div className="min-w-0">
            <p
              className={cn(
                'text-2xl leading-none font-semibold tracking-[-0.02em] uppercase sm:text-3xl',
                VERDICT_TEXT[verdict],
              )}
            >
              {VERDICT_LABEL[verdict]}
            </p>
            {summary && (
              <p className="text-ink mt-3 max-w-[32ch] font-serif text-lg leading-snug sm:text-xl">
                {summary}
              </p>
            )}
          </div>

          <ScoreMeter
            score={score}
            verdict={verdict}
            size="md"
            className="w-full shrink-0 sm:w-52"
          />
        </div>

        {price && best && (
          <div className="border-line border-t pt-5">
            <span className="label text-graphite">Better price found</span>
            <PriceDrop from={price} to={best} saving={saving} size="md" className="mt-3" />
          </div>
        )}

        {showSignals && signals.length > 0 && (
          <div className="border-line border-t pt-5">
            <span className="label text-graphite">Why</span>
            <SignalList signals={signals} className="mt-3" />
          </div>
        )}
      </div>
    </div>
  )
}
