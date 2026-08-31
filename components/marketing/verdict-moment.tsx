import { Disclosure } from './section'
import { cn } from '@/lib/utils/cn'

/**
 * Beat 05 — the verdict, and why.
 *
 * The page's centre of gravity. A full-bleed scene rather than a section with
 * columns: the score arrives at display scale, dead centre, on a banded rule
 * that shows 61 sitting inside "think twice" rather than asserting it. Then the
 * six things Worth actually weighed, full width and legible, so the number is
 * visibly the conclusion of an argument rather than a mood.
 *
 * The hero shows this reveal in miniature as the launch shot. This is where it
 * gets the room to be the point of the page.
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
    <section className="scene scene-in scene-out relative overflow-hidden py-24 sm:py-32">
      <div className="relative mx-auto max-w-4xl px-5 text-center sm:px-6">
        <p className="label text-white/40">05 · The answer</p>

        <p className="tnum text-display mt-8 font-semibold text-white">
          {score}
          <span className="text-[0.2em] font-normal tracking-normal text-white/30"> /100</span>
        </p>

        <Scale score={score} />

        <p className="text-think-lift text-statement mt-10 font-serif font-medium">Think twice</p>

        <p className="text-statement mx-auto mt-4 max-w-[18ch] font-serif font-medium text-white">
          The product is good. The price isn’t.
        </p>
      </div>

      {/* The reasoning, full width. */}
      <div className="relative mx-auto mt-20 max-w-4xl px-5 sm:px-6">
        <p className="label border-b border-white/10 pb-4 text-white/40">
          What Worth weighed
        </p>
        <ul className="flex flex-col divide-y divide-white/8">
          {SIGNALS.map(([label, detail, tone]) => (
            <li key={label} className="flex items-baseline gap-4 py-5 sm:gap-6">
              <span
                className={cn('size-2 shrink-0 translate-y-[-1px] rounded-full', DOT[tone])}
                aria-hidden
              />
              <span className="text-page w-[6.5rem] shrink-0 font-medium text-white sm:w-40">
                {label}
              </span>
              <span className="text-lead text-white/55">{detail}</span>
            </li>
          ))}
        </ul>

        <Disclosure tone="dark" className="mt-10">
          Illustrative analysis — not a real product evaluation.
        </Disclosure>
      </div>
    </section>
  )
}

/**
 * The banded scale. The verdict thresholds are drawn, so 61 is visibly inside
 * "think twice" rather than being told it is.
 */
function Scale({ score }: { score: number }) {
  const ticks = Array.from({ length: 21 }, (_, i) => i * 5)
  return (
    <div className="mx-auto mt-8 max-w-lg">
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
