import type { Verdict } from '@/lib/analysis/types'
import { VERDICT_LABEL } from '@/lib/analysis/verdict'
import { formatMoney, moneyDelta } from '@/lib/analysis/format'
import { cn } from '@/lib/utils/cn'

const ACCENT: Record<Verdict, string> = {
  buy: 'text-[#5FD3A3]',
  think_twice: 'text-[#F0B65C]',
  skip: 'text-[#F2836E]',
}

const BAND: Record<Verdict, string> = {
  buy: 'bg-[#5FD3A3]',
  think_twice: 'bg-[#F0B65C]',
  skip: 'bg-[#F2836E]',
}

/**
 * The share card — Worth's social object.
 *
 * 4:5 portrait, the ratio that fills a phone screen in a feed. It is designed
 * to be screenshotted and posted, which means it has to work with no context,
 * at thumbnail size, next to somebody's photos. So:
 *
 *   - Worth Blue holds the top edge and the wordmark, making the card
 *     recognisable as Worth before a single word is read.
 *   - The score and the price drop are the only large elements; everything
 *     else recedes.
 *   - The same band scale as the rest of the product appears at the bottom,
 *     so a shared card and a real result are visibly the same object.
 *
 * It is markup rather than an image, so the result page, the public share page
 * and later server-side OG rendering all use this one component.
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
        'rounded-object bg-ink relative flex aspect-[4/5] w-full flex-col overflow-hidden text-white',
        className,
      )}
    >
      {/* Brand edge — the first thing recognisable at thumbnail size. */}
      <span className="bg-worth absolute inset-x-0 top-0 h-1.5" aria-hidden />

      <div className="flex items-center justify-between px-5 pt-6 pb-3 sm:px-6">
        <span className="font-serif text-lg font-medium tracking-[-0.01em] text-white">Worth</span>
        <span className="label text-white/35">Illustrative</span>
      </div>

      <div className="flex flex-1 flex-col justify-center gap-5 px-5 sm:px-6">
        {/* The score, dominant. */}
        <div className="flex items-end gap-2.5">
          <span
            className={cn(
              'tnum text-[4.25rem] leading-[0.82] font-semibold tracking-[-0.055em] sm:text-[5rem]',
              ACCENT[verdict],
            )}
          >
            {score}
          </span>
          <div className="pb-1.5">
            <span className="tnum block text-sm font-medium text-white/35">/100</span>
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
          <p className="font-serif text-xl leading-[1.2] text-white sm:text-2xl">{summary}</p>
        )}

        {price && best && (
          <div className="flex items-baseline gap-2.5">
            <span className="tnum text-xl font-medium text-white/35 line-through decoration-1">
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
                stroke="var(--color-worth)"
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

      {/* The band scale — the same instrument as the rest of the product. */}
      <div className="px-5 pb-5 sm:px-6 sm:pb-6">
        {title && <p className="mb-3 truncate text-[0.8125rem] text-white/45">{title}</p>}
        <div className="relative h-4">
          <div className="absolute inset-x-0 top-2 flex justify-between">
            {Array.from({ length: 21 }, (_, i) => i * 5).map((tick) => (
              <span
                key={tick}
                className={cn(
                  'w-px',
                  tick % 25 === 0 ? 'h-2.5' : 'h-1.5',
                  tick <= score ? 'bg-white/45' : 'bg-white/15',
                )}
              />
            ))}
          </div>
          <div className="absolute top-0 -translate-x-1/2" style={{ left: `${score}%` }}>
            <span className={cn('block h-4 w-[3px] rounded-full', BAND[verdict])} />
          </div>
        </div>
      </div>
    </div>
  )
}
