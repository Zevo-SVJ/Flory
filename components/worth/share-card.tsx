import type { Verdict } from '@/lib/analysis/types'
import { VERDICT_LABEL } from '@/lib/analysis/verdict'
import { formatMoney, moneyDelta } from '@/lib/analysis/format'
import { cn } from '@/lib/utils/cn'

const ACCENT: Record<Verdict, string> = {
  buy: 'text-buy-lift',
  think_twice: 'text-think-lift',
  skip: 'text-skip-lift',
}

const MARK: Record<Verdict, string> = {
  buy: 'bg-buy-lift',
  think_twice: 'bg-think-lift',
  skip: 'bg-skip-lift',
}

/**
 * The share card — Worth's social object.
 *
 * 4:5 portrait, the ratio that fills a phone screen in a feed. It has to work
 * with no context, at thumbnail size, next to somebody's holiday photos. So:
 *
 *   - Violet stage lighting and the wordmark hold the top, making it
 *     recognisable as Worth before a word is read.
 *   - The score and the price drop are the only large elements.
 *   - The banded scale at the bottom is the same instrument as the rest of the
 *     product, so a shared card and a real result are visibly one object.
 *
 * Markup rather than an image, so the result page, the public share page and
 * later server-side OG rendering all use this component.
 */
export function ShareCard({
  score,
  verdict,
  title,
  summary,
  priceMinor,
  bestPriceMinor,
  currency,
  className,
}: {
  score: number
  verdict: Verdict
  title: string | null
  summary: string | null
  priceMinor: number | null
  bestPriceMinor: number | null
  currency: string
  className?: string
}) {
  const price = formatMoney(priceMinor, currency)
  const best = formatMoney(bestPriceMinor, currency)
  const delta = moneyDelta(priceMinor, bestPriceMinor)
  const saving = delta ? formatMoney(delta.savingMinor, currency) : null

  return (
    <div
      className={cn(
        'stage-light rounded-stage relative flex aspect-[4/5] w-full flex-col overflow-hidden',
        'border-midnight-line bg-midnight border text-white',
        className,
      )}
    >
      <div className="flex items-center justify-between px-6 pt-6 pb-4">
        <span className="font-serif text-xl font-medium tracking-[-0.01em] text-white">
          Worth<span className="text-violet-lift">.</span>
        </span>
        <span className="label text-white/30">Illustrative</span>
      </div>

      <div className="flex flex-1 flex-col justify-center gap-5 px-6">
        <div className="flex items-end gap-3">
          <span
            className={cn(
              'tnum text-[4.75rem] leading-[0.8] font-semibold tracking-[-0.06em] sm:text-[5.5rem]',
              ACCENT[verdict],
            )}
          >
            {score}
          </span>
          <div className="pb-2">
            <span className="tnum block text-sm font-medium text-white/30">/100</span>
            <span
              className={cn(
                'block text-lg leading-none font-semibold tracking-[-0.01em] uppercase sm:text-xl',
                ACCENT[verdict],
              )}
            >
              {VERDICT_LABEL[verdict]}
            </span>
          </div>
        </div>

        {summary && (
          <p className="font-serif text-[1.375rem] leading-[1.15] text-white sm:text-2xl">
            {summary}
          </p>
        )}

        {price && best && (
          <div className="flex items-baseline gap-2.5">
            <span className="tnum text-xl font-medium text-white/30 line-through decoration-1">
              {price}
            </span>
            <svg
              width="20"
              height="11"
              viewBox="0 0 22 12"
              fill="none"
              aria-hidden
              className="self-center"
            >
              <path
                d="M0 6h19M14.5 1.5 19.5 6l-5 4.5"
                stroke="var(--color-violet-lift)"
                strokeWidth="2"
                strokeLinecap="square"
              />
            </svg>
            <span className="tnum text-2xl font-semibold tracking-[-0.03em] text-white sm:text-3xl">
              {best}
            </span>
          </div>
        )}

        {saving && (
          <p className={cn('tnum text-base font-semibold', ACCENT.buy)}>
            {saving} potential saving
          </p>
        )}
      </div>

      <div className="px-6 pb-6">
        {title && <p className="mb-3.5 truncate text-[0.8125rem] text-white/40">{title}</p>}
        <div className="relative h-4">
          <div className="absolute inset-x-0 top-2 flex justify-between">
            {Array.from({ length: 21 }, (_, i) => i * 5).map((tick) => (
              <span
                key={tick}
                className={cn(
                  'w-px',
                  tick % 25 === 0 ? 'h-2.5' : 'h-1.5',
                  tick <= score ? 'bg-white/45' : 'bg-white/12',
                )}
              />
            ))}
          </div>
          <div className="absolute top-0 -translate-x-1/2" style={{ left: `${score}%` }}>
            <span className={cn('block h-4 w-[3px] rounded-full', MARK[verdict])} />
          </div>
        </div>
      </div>
    </div>
  )
}
