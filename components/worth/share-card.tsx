import type { Verdict } from '@/lib/analysis/types'
import { VERDICT_LABEL } from '@/lib/analysis/verdict'
import { formatMoney, moneyDelta } from '@/lib/analysis/format'
import { cn } from '@/lib/utils/cn'

const LIFT: Record<Verdict, string> = {
  buy: 'text-buy-lift',
  think_twice: 'text-think-lift',
  skip: 'text-skip-lift',
}

const RING: Record<Verdict, string> = {
  buy: 'stroke-buy-lift',
  think_twice: 'stroke-think-lift',
  skip: 'stroke-skip-lift',
}

/**
 * The shareable result — Worth's social object.
 *
 * 4:5 portrait, the aspect ratio that fills a phone screen in a feed. It
 * deliberately inverts the design system onto ink so that a screenshot is
 * instantly recognisable as Worth wherever it travels, and so the verdict
 * survives being viewed at thumbnail size.
 *
 * Rendered as real markup rather than an image, so the same component serves
 * the result page, the public share page and (later) server-side image
 * generation for Open Graph.
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
  const delta = moneyDelta(priceMinor, bestPriceMinor)
  const saving = delta ? formatMoney(delta.savingMinor, currency) : null

  const radius = 46
  const circumference = 2 * Math.PI * radius

  return (
    <div
      className={cn(
        'rounded-card flex aspect-[4/5] w-full flex-col justify-between overflow-hidden',
        'bg-ink text-paper p-5 sm:p-7',
        className,
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-[0.8125rem] font-semibold tracking-[0.18em] uppercase">Worth</span>
        <span className="text-paper/45 text-[0.625rem] tracking-[0.12em] uppercase">Example</span>
      </div>

      <div className="flex flex-col gap-4">
        {price && (
          <p className="text-paper/70 font-serif text-[1.0625rem] leading-snug sm:text-xl">
            I almost bought this for <span className="tnum text-paper">{price}</span>.
          </p>
        )}

        <div className="flex items-center gap-4">
          <div className="relative size-[104px] shrink-0">
            <svg viewBox="0 0 104 104" className="size-full" aria-hidden>
              <circle
                cx="52"
                cy="52"
                r={radius}
                fill="none"
                className="stroke-paper/15"
                strokeWidth="7"
              />
              <circle
                cx="52"
                cy="52"
                r={radius}
                fill="none"
                className={RING[verdict]}
                strokeWidth="7"
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={circumference * (1 - score / 100)}
                transform="rotate(-90 52 52)"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className={cn('tnum text-[2rem] leading-none font-semibold', LIFT[verdict])}>
                {score}
              </span>
              <span className="tnum text-paper/50 mt-0.5 text-[0.625rem]">/ 100</span>
            </div>
          </div>

          <div className="min-w-0">
            <p
              className={cn(
                'text-[2rem] leading-none font-semibold tracking-[-0.02em] uppercase sm:text-[2.5rem]',
                LIFT[verdict],
              )}
            >
              {VERDICT_LABEL[verdict]}
            </p>
            {title && <p className="text-paper/55 mt-2 truncate text-[0.8125rem]">{title}</p>}
          </div>
        </div>

        {summary && (
          <p className="text-paper/85 font-serif text-[1.0625rem] leading-snug sm:text-lg">
            {summary}
          </p>
        )}

        {saving && (
          <div className="border-paper/15 border-t pt-3">
            <p className="text-paper/50 text-[0.625rem] font-medium tracking-[0.12em] uppercase">
              Potential saving
            </p>
            <p className="tnum text-buy-lift mt-1 text-2xl font-semibold sm:text-3xl">{saving}</p>
          </div>
        )}
      </div>

      {/* The loop: whoever sees this card knows what to do next. */}
      <p className="text-paper/45 text-[0.75rem]">Check something you’re thinking about buying →</p>
    </div>
  )
}
