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
      {/* Brand first: this has to be recognisable as Worth in a feed, at
          thumbnail size, before a word of it is read. */}
      <div className="flex items-center justify-between px-6 pt-6 pb-2">
        <span className="font-serif text-xl font-medium tracking-[-0.01em] text-white">
          Worth<span className="text-violet-lift">.</span>
        </span>
        <span className="label text-white/30">Illustrative</span>
      </div>

      {/* The story, in the order someone would tell it out loud: what I was
          about to pay, what Worth found, what that saves. The verdict closes
          it. Nothing else is on the card. */}
      <div className="flex flex-1 flex-col justify-center gap-1 px-6">
        <span className="label text-white/40">I almost spent</span>
        {price && (
          <p className="tnum text-[2.75rem] leading-none font-semibold tracking-[-0.05em] text-white/35 line-through decoration-2 sm:text-[3.25rem]">
            {price}
          </p>
        )}

        <span className="label mt-6 text-white/40">Worth found</span>
        {best && (
          <p className="tnum text-[3.75rem] leading-none font-semibold tracking-[-0.055em] text-white sm:text-[4.5rem]">
            {best}
          </p>
        )}

        {saving && (
          <p className={cn('tnum mt-3 text-2xl font-semibold sm:text-[1.75rem]', ACCENT.buy)}>
            {saving} less
          </p>
        )}
      </div>

      <div className="border-t border-white/10 px-6 py-5">
        <div className="flex items-end justify-between gap-4">
          <div className="min-w-0">
            <span
              className={cn(
                'block text-[1.25rem] leading-none font-semibold tracking-[-0.015em] uppercase sm:text-[1.375rem]',
                ACCENT[verdict],
              )}
            >
              {VERDICT_LABEL[verdict]}
            </span>
            {summary && (
              <p className="mt-2.5 line-clamp-2 font-serif text-[1rem] leading-snug text-white/75">
                {summary}
              </p>
            )}
          </div>

          <span className="tnum flex shrink-0 items-baseline gap-1">
            <span
              className={cn(
                'text-[2.5rem] leading-none font-semibold tracking-[-0.05em]',
                ACCENT[verdict],
              )}
            >
              {score}
            </span>
            <span className="text-[0.75rem] text-white/30">/100</span>
          </span>
        </div>

        {title && <p className="mt-4 truncate text-[0.75rem] text-white/35">{title}</p>}

        {/* The same banded scale as the product itself, so a shared card and a
            real result are visibly one object. */}
        <div className="relative mt-3 h-4">
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
