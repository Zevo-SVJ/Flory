import { Section, Eyebrow, Disclosure } from './section'
import { cn } from '@/lib/utils/cn'

/**
 * Beat 05 — the verdict.
 *
 * The page's centre of gravity, and the one moment Worth stops gathering and
 * commits. Dark stage with violet lighting, the score at display scale on a
 * banded scale so the conclusion is visibly derived from the number rather
 * than asserted next to it.
 *
 * Set inline rather than inside a card: a card would make the verdict one more
 * element on the page instead of the thing the page is for.
 */

const SIGNALS = [
  ['Price', '€70 above the best verified price', 'negative'],
  ['Reviews', 'Battery and call quality consistently praised', 'positive'],
  ['Trust', 'Verified seller, 30-day returns, 2-year warranty', 'positive'],
  ['Value', 'Top of its class for noise cancelling', 'positive'],
  ['Risk', 'A refresh is expected within six months', 'caution'],
  ['Alternatives', 'Identical model, verified retailer, €329', 'positive'],
] as const

const DOT = {
  positive: 'bg-buy-lift',
  negative: 'bg-skip-lift',
  caution: 'bg-think-lift',
} as const

export function VerdictMoment() {
  const score = 61

  return (
    <Section tone="dark" glow>
      <Eyebrow index="05" tone="dark">
        The answer
      </Eyebrow>

      <div className="mt-8 grid grid-cols-1 gap-12 lg:mt-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)] lg:gap-20">
        <div>
          <div className="flex items-end gap-3">
            <span className="tnum text-score font-semibold text-white">{score}</span>
            <span className="tnum pb-3 text-lg font-medium text-white/35 sm:pb-4">/100</span>
          </div>

          <Scale score={score} />

          <p className="text-think-lift mt-8 text-3xl leading-none font-semibold tracking-[-0.025em] uppercase sm:text-4xl">
            Think twice
          </p>

          <p className="text-statement mt-5 max-w-[18ch] font-serif leading-[1.05] font-medium text-white">
            The product is good. The price isn’t.
          </p>
        </div>

        <div className="flex flex-col gap-9 lg:pt-6">
          <div>
            <span className="label text-white/45">What it costs you</span>
            <div className="mt-5 flex flex-wrap items-baseline gap-x-4 gap-y-2">
              <span className="tnum text-3xl font-medium text-white/30 line-through decoration-1 sm:text-4xl">
                €399
              </span>
              <svg
                width="28"
                height="15"
                viewBox="0 0 22 12"
                fill="none"
                aria-hidden
                className="self-center"
              >
                <path
                  d="M0 6h19M14.5 1.5 19.5 6l-5 4.5"
                  stroke="var(--color-violet-lift)"
                  strokeWidth="1.8"
                  strokeLinecap="square"
                />
              </svg>
              <span className="tnum text-4xl font-semibold tracking-[-0.035em] text-white sm:text-5xl">
                €329
              </span>
            </div>
            <p className="tnum text-buy-lift mt-4 text-lg font-semibold">€70 potential saving</p>
          </div>

          <div className="border-t border-white/10 pt-7">
            <span className="label text-white/45">Why</span>
            <ul className="mt-5 flex flex-col divide-y divide-white/8">
              {SIGNALS.map(([label, detail, tone]) => (
                <li key={label} className="flex items-start gap-3 py-3">
                  <span
                    className={cn('mt-1.5 size-1.5 shrink-0 rounded-full', DOT[tone])}
                    aria-hidden
                  />
                  <span className="text-[0.875rem] leading-snug text-white/60">
                    <span className="font-semibold text-white">{label}</span> · {detail}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <Disclosure tone="dark" className="mt-12">
        Illustrative analysis — not a real product evaluation.
      </Disclosure>
    </Section>
  )
}

/**
 * The banded scale. The verdict thresholds are drawn, so 61 is visibly inside
 * "think twice" rather than being told it is.
 */
function Scale({ score }: { score: number }) {
  const ticks = Array.from({ length: 21 }, (_, i) => i * 5)
  return (
    <div className="mt-6 max-w-lg">
      <div className="relative h-8">
        <div className="absolute inset-x-0 top-4 flex justify-between">
          {ticks.map((tick) => (
            <span
              key={tick}
              className={cn(
                'w-px',
                tick % 25 === 0 ? 'h-4' : 'h-2',
                tick <= score ? 'bg-white/55' : 'bg-white/15',
              )}
            />
          ))}
        </div>
        <div className="absolute top-0 -translate-x-1/2" style={{ left: `${score}%` }}>
          <span className="bg-think-lift block h-8 w-[3px] rounded-full" />
        </div>
      </div>
      <div className="label mt-2 flex text-white/30">
        <span className="flex-1 text-left">Skip</span>
        <span className="text-think-lift flex-1 text-center">Think twice</span>
        <span className="flex-1 text-right">Buy</span>
      </div>
    </div>
  )
}
