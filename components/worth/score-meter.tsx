import type { Verdict } from '@/lib/analysis/types'
import { VERDICT_LABEL, VERDICT_THRESHOLDS } from '@/lib/analysis/verdict'
import { cn } from '@/lib/utils/cn'

const TEXT: Record<Verdict, string> = {
  buy: 'text-buy',
  think_twice: 'text-think',
  skip: 'text-skip',
}

const MARK: Record<Verdict, string> = {
  buy: 'bg-buy',
  think_twice: 'bg-think',
  skip: 'bg-skip',
}

/**
 * The Worth Score, drawn as a measuring instrument.
 *
 * Deliberately not a donut chart. A donut says "dashboard widget" and hides
 * the thing that actually matters: a score of 61 means nothing until you can
 * see that 61 falls inside the "think twice" band. The scale shows the bands,
 * so the verdict is visibly a consequence of the number rather than a separate
 * claim beside it.
 *
 * This is Worth's primary brand object — it appears on the hero, the result
 * page, the share card and every history row, always with the same bands and
 * the same tick treatment.
 */
export function ScoreMeter({
  score,
  verdict,
  size = 'lg',
  animate = false,
  showScore = true,
  className,
}: {
  score: number
  verdict: Verdict
  size?: 'sm' | 'md' | 'lg'
  animate?: boolean
  /** Off where the score is already set larger alongside the scale. */
  showScore?: boolean
  className?: string
}) {
  const ticks = Array.from({ length: 21 }, (_, i) => i * 5)

  return (
    <div className={cn('flex flex-col gap-2.5', className)}>
      {showScore && (
        <div className="flex items-end gap-2.5">
          <span
            className={cn(
              'tnum leading-none font-semibold tracking-[-0.05em]',
              TEXT[verdict],
              size === 'lg' ? 'text-score' : size === 'md' ? 'text-[3.25rem]' : 'text-[2rem]',
              animate && 'anim-settle',
            )}
          >
            {score}
          </span>
          <span
            className={cn(
              'tnum text-faint pb-1 font-medium',
              size === 'lg' ? 'text-lg' : size === 'md' ? 'text-sm' : 'text-xs',
            )}
          >
            /100
          </span>
        </div>
      )}

      {/* The scale. Band boundaries are the real verdict thresholds. */}
      <div className="flex flex-col gap-1.5">
        <div
          className="relative h-6 w-full"
          role="img"
          aria-label={`Worth Score ${score} of 100 — ${VERDICT_LABEL[verdict]}`}
        >
          <div className="absolute inset-x-0 top-3 flex justify-between">
            {ticks.map((tick) => {
              const major = tick % 25 === 0
              const passed = tick <= score
              return (
                <span
                  key={tick}
                  className={cn(
                    'w-px origin-top transition-colors',
                    major ? 'h-3' : 'h-1.5',
                    passed ? 'bg-ink/45' : 'bg-line-strong',
                  )}
                />
              )
            })}
          </div>

          {/* The marker. */}
          <div className="absolute top-0 -translate-x-1/2" style={{ left: `${score}%` }}>
            <span className={cn('block h-6 w-[3px] rounded-full', MARK[verdict])} />
          </div>
        </div>

        {/* Thirds rather than justify-between: each label owns its share of the
            track, so they cannot collide however narrow the meter gets. */}
        <div className="label text-faint flex">
          <span
            className={cn('flex-1 text-left', score < VERDICT_THRESHOLDS.thinkTwice && TEXT.skip)}
          >
            Skip
          </span>
          <span
            className={cn(
              'flex-1 text-center',
              score >= VERDICT_THRESHOLDS.thinkTwice &&
                score < VERDICT_THRESHOLDS.buy &&
                TEXT.think_twice,
            )}
          >
            Think twice
          </span>
          <span className={cn('flex-1 text-right', score >= VERDICT_THRESHOLDS.buy && TEXT.buy)}>
            Buy
          </span>
        </div>
      </div>
    </div>
  )
}

/** The compact score chip used in lists, where the full scale won't fit. */
export function ScoreChip({
  score,
  verdict,
  className,
}: {
  score: number
  verdict: Verdict
  className?: string
}) {
  return (
    <span
      className={cn(
        'tnum rounded-note inline-flex h-11 w-11 shrink-0 items-center justify-center',
        'border text-[0.9375rem] font-semibold',
        verdict === 'buy' && 'border-buy/25 bg-buy-wash text-buy',
        verdict === 'think_twice' && 'border-think/25 bg-think-wash text-think',
        verdict === 'skip' && 'border-skip/25 bg-skip-wash text-skip',
        className,
      )}
    >
      {score}
    </span>
  )
}
