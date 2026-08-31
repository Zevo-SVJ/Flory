import { Section } from './section'
import { PRIMARY_EXAMPLE } from '@/lib/analysis/fixtures'
import { VERDICT_THRESHOLDS } from '@/lib/analysis/verdict'

/**
 * The verdict — the page's centre of gravity.
 *
 * Full-bleed ink, because this is the one moment where Worth stops gathering
 * and commits. The score is set at display scale with the band scale beneath
 * it, so the conclusion is visibly derived rather than asserted.
 *
 * Rendered dark and inline rather than as a card: a card would make the
 * verdict one more element on the page instead of the thing the page is for.
 */
export function VerdictMoment() {
  const score = PRIMARY_EXAMPLE.score ?? 61

  return (
    <Section tone="ink">
      <div className="flex flex-col gap-3">
        <div className="flex items-baseline gap-3">
          <span className="tnum label text-worth">04</span>
          <span className="label text-white/45">The answer</span>
        </div>
      </div>

      <div className="mt-10 grid grid-cols-1 gap-10 lg:mt-14 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.95fr)] lg:gap-16">
        <div>
          <div className="flex items-end gap-3">
            <span className="tnum text-score leading-[0.84] font-semibold tracking-[-0.055em] text-white">
              {score}
            </span>
            <span className="tnum pb-2 text-lg font-medium text-white/40 sm:pb-3">/100</span>
          </div>

          {/* The same band scale as everywhere else, inverted for ink. */}
          <DarkScale score={score} />

          <p className="text-think mt-7 text-3xl leading-none font-semibold tracking-[-0.025em] uppercase sm:text-4xl">
            Think twice
          </p>

          <p className="text-statement mt-4 max-w-[24ch] font-serif leading-[1.1] font-medium text-white">
            {PRIMARY_EXAMPLE.summary}
          </p>
        </div>

        <div className="flex flex-col gap-8 lg:pt-4">
          <div>
            <span className="label text-white/45">What it costs you</span>
            <div className="mt-4 flex flex-wrap items-baseline gap-x-4 gap-y-2">
              <span className="tnum text-3xl font-medium text-white/35 line-through decoration-1 sm:text-4xl">
                €399
              </span>
              <svg
                width="26"
                height="14"
                viewBox="0 0 22 12"
                fill="none"
                aria-hidden
                className="self-center"
              >
                <path
                  d="M0 6h19M14.5 1.5 19.5 6l-5 4.5"
                  stroke="var(--color-worth)"
                  strokeWidth="1.75"
                  strokeLinecap="square"
                />
              </svg>
              <span className="tnum text-4xl font-semibold tracking-[-0.035em] text-white sm:text-5xl">
                €329
              </span>
            </div>
            <p className="tnum text-buy mt-3 text-lg font-semibold">€70 potential saving</p>
          </div>

          <div className="border-t border-white/12 pt-6">
            <span className="label text-white/45">Why</span>
            <ul className="mt-4 flex flex-col divide-y divide-white/10">
              {(PRIMARY_EXAMPLE.result?.signals ?? []).map((signal) => (
                <li key={signal.kind} className="flex items-start gap-3 py-2.5">
                  <span
                    className={`mt-1.5 size-1.5 shrink-0 rounded-full ${
                      signal.tone === 'positive'
                        ? 'bg-buy'
                        : signal.tone === 'negative'
                          ? 'bg-skip'
                          : signal.tone === 'caution'
                            ? 'bg-think'
                            : 'bg-white/40'
                    }`}
                    aria-hidden
                  />
                  <span className="text-[0.875rem] leading-snug text-white/70">
                    <span className="font-semibold text-white">{signal.label}</span> ·{' '}
                    {signal.detail}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <p className="mt-10 text-[0.75rem] text-white/35">
        Illustrative analysis — not a real product evaluation.
      </p>
    </Section>
  )
}

/** The band scale, inverted. Same geometry as ScoreMeter so it reads as one system. */
function DarkScale({ score }: { score: number }) {
  const ticks = Array.from({ length: 21 }, (_, i) => i * 5)
  return (
    <div className="mt-5 max-w-md">
      <div className="relative h-7">
        <div className="absolute inset-x-0 top-3.5 flex justify-between">
          {ticks.map((tick) => (
            <span
              key={tick}
              className={`w-px ${tick % 25 === 0 ? 'h-3.5' : 'h-2'} ${
                tick <= score ? 'bg-white/55' : 'bg-white/18'
              }`}
            />
          ))}
        </div>
        <div className="absolute top-0 -translate-x-1/2" style={{ left: `${score}%` }}>
          <span className="bg-think block h-7 w-[3px] rounded-full" />
        </div>
      </div>
      <div className="label mt-1.5 flex justify-between text-white/35">
        <span>Skip</span>
        <span
          className={
            score >= VERDICT_THRESHOLDS.thinkTwice && score < VERDICT_THRESHOLDS.buy
              ? 'text-think'
              : ''
          }
        >
          Think twice
        </span>
        <span>Buy</span>
      </div>
    </div>
  )
}
