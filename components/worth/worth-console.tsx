'use client'

import { useEffect, useState } from 'react'
import { PRIMARY_EXAMPLE } from '@/lib/analysis/fixtures'
import { cn } from '@/lib/utils/cn'

/**
 * The Worth console — the product, as an object.
 *
 * This is the one piece of interface the landing page shows, and it is built to
 * be looked at rather than read: dark glass, a lit rim, a halo behind it, and
 * two smaller panels sitting off its back edge so it has thickness. It is not a
 * screenshot dropped into a div; it is the centrepiece of the scene.
 *
 * It builds itself in the order the product works:
 *
 *   1  a link is there
 *   2  Worth starts reading it
 *   3  the six dimensions resolve, one at a time, into the ring
 *   4  the ring closes on the score
 *   5  the verdict lands
 *   6  the money follows
 *
 * Everything moves on `transform` and `opacity` only. Under
 * prefers-reduced-motion the finished console renders immediately, with no
 * entrance and no transforms.
 *
 * Every figure is illustrative — Worth's research engine isn't connected, so
 * the verdict is authored. The disclosure lives on the section that hosts this.
 */

const DIMENSIONS = [
  { label: 'Price', value: '€892 advertised', tone: 'caution' },
  { label: 'Fees', value: '€115 at checkout', tone: 'negative' },
  { label: 'Reviews', value: '4.5 · 1,284', tone: 'positive' },
  { label: 'Trust', value: 'Established seller', tone: 'positive' },
  { label: 'Risk', value: 'Locked in at 14 days', tone: 'negative' },
  { label: 'Alternatives', value: '€724 elsewhere', tone: 'positive' },
] as const

const TONE = {
  positive: 'text-buy-lift',
  caution: 'text-think-lift',
  negative: 'text-skip-lift',
} as const

const DOT = {
  positive: 'bg-buy-lift',
  caution: 'bg-think-lift',
  negative: 'bg-skip-lift',
} as const

const SCORE = PRIMARY_EXAMPLE.score ?? 68

/* One entry per step, in ms from mount. */
const STEP_READING = 1
const STEP_FIRST_DIM = 2
const STEP_RING = STEP_FIRST_DIM + DIMENSIONS.length
const STEP_VERDICT = STEP_RING + 1
const STEP_MONEY = STEP_VERDICT + 1
const TIMELINE = [520, 900, 1040, 1180, 1320, 1460, 1600, 1820, 2160, 2460]

if (TIMELINE.length !== STEP_MONEY) {
  throw new Error(`WorthConsole timeline has ${TIMELINE.length} steps, needs ${STEP_MONEY}`)
}

export function WorthConsole({ className }: { className?: string }) {
  const [step, setStep] = useState(0)
  const [score, setScore] = useState(0)
  const [still, setStill] = useState(false)

  const reading = step >= STEP_READING && step < STEP_RING
  const ringed = step >= STEP_RING
  const resolved = step >= STEP_VERDICT
  const dimsDone = Math.max(0, Math.min(step - STEP_FIRST_DIM + 1, DIMENSIONS.length))

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      const skip = window.setTimeout(() => {
        setStill(true)
        setStep(STEP_MONEY)
        setScore(SCORE)
      }, 0)
      return () => window.clearTimeout(skip)
    }
    const timers = TIMELINE.map((at, i) => window.setTimeout(() => setStep(i + 1), at))
    return () => timers.forEach(window.clearTimeout)
  }, [])

  useEffect(() => {
    if (!ringed || score >= SCORE || still) return
    const tick = window.setInterval(() => setScore((c) => Math.min(c + 2, SCORE)), 16)
    return () => window.clearInterval(tick)
  }, [ringed, score, still])

  return (
    <div className={cn('relative', className)}>
      {/* The two layers behind the console. They exist only to give it a back,
          so the object has thickness rather than being a rectangle on a
          gradient — which is why they are edges, not panels: a tall panel
          behind a taller one just reads as a stray shape. */}
      <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 -z-10">
        <div
          className={cn(
            'glass absolute inset-x-[5%] -top-4 h-10 rounded-t-[1.5rem] opacity-50',
            still ? '' : 'motion-safe:anim-rise-2',
          )}
        />
        <div
          className={cn(
            'glass absolute inset-x-[11%] -top-8 h-10 rounded-t-[1.5rem] opacity-25',
            still ? '' : 'motion-safe:anim-rise-3',
          )}
        />
      </div>

      {/* The halo. Lights the space the console stands in — on its own
          element, since on the console it would sit behind the glass fill. */}
      <div aria-hidden className="halo pointer-events-none absolute inset-[8%] -z-20" />

      <div
        className={cn(
          'glass glass-rim rounded-stage relative overflow-hidden',
          still ? '' : 'motion-safe:anim-rise-1',
        )}
      >
        {/* Head: what is being looked at. */}
        <div className="flex items-center gap-3 border-b border-white/8 px-5 py-4 sm:px-7 sm:py-5">
          <span
            aria-hidden
            className={cn(
              'size-1.5 shrink-0 rounded-full transition-colors duration-500',
              resolved ? 'bg-buy-lift' : 'bg-electric motion-safe:animate-pulse',
            )}
          />
          <span className="min-w-0 flex-1 truncate font-mono text-[0.8125rem] text-white/55">
            example.com/checkout
          </span>
          <span
            className={cn(
              'label shrink-0 transition-colors duration-500',
              resolved ? 'text-buy-lift' : 'text-electric',
            )}
          >
            {resolved ? 'Done' : 'Reading'}
          </span>
        </div>

        {/* The scan. One pass across the console while the dimensions resolve. */}
        {reading && !still && (
          <div aria-hidden className="anim-sweep pointer-events-none absolute inset-0 z-10" />
        )}

        <div className="grid grid-cols-1 gap-7 px-5 py-7 sm:px-7 sm:py-8 lg:grid-cols-[minmax(0,1fr)_auto] lg:gap-10">
          {/* What Worth found. */}
          <ul className="flex flex-col gap-3.5">
            {DIMENSIONS.map((d, i) => (
              <li
                key={d.label}
                className={cn(
                  'flex items-baseline gap-3 border-b border-white/6 pb-3.5 last:border-0 last:pb-0',
                  i < dimsDone ? 'motion-safe:anim-land' : 'invisible',
                )}
                style={{ animationDelay: `${i * 20}ms` }}
              >
                <span aria-hidden className={cn('size-1.5 shrink-0 rounded-full', DOT[d.tone])} />
                <span className="label w-[6.75rem] shrink-0 text-white/40">{d.label}</span>
                <span className={cn('text-[0.875rem] leading-snug', TONE[d.tone])}>{d.value}</span>
              </li>
            ))}
          </ul>

          {/* The score, as an instrument. */}
          <div className="flex items-center justify-center lg:w-[13rem]">
            <ScoreRing score={score} settled={ringed} />
          </div>
        </div>

        {/* The conclusion. */}
        <div className="border-t border-white/8 px-5 py-6 sm:px-7">
          <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
            <div className={cn('min-w-0', resolved ? 'motion-safe:anim-wipe' : 'invisible')}>
              <p className="label text-white/35">Verdict</p>
              <p className="text-think-lift mt-2 font-serif text-[1.75rem] leading-none font-medium tracking-[-0.02em] sm:text-[2.125rem]">
                Think twice
              </p>
            </div>

            <div
              className={cn(
                'flex items-center gap-3',
                step >= STEP_MONEY ? 'motion-safe:anim-land' : 'invisible',
              )}
            >
              <span className="tnum text-[1.125rem] text-white/25 line-through">€1,007</span>
              <span aria-hidden className="text-electric">
                →
              </span>
              <span className="tnum text-[1.75rem] leading-none font-semibold tracking-[-0.03em] text-white">
                €724
              </span>
              <span className="bg-buy/20 text-buy-lift rounded-full px-2.5 py-1 text-[0.75rem] font-medium">
                −€283
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * The score ring.
 *
 * A dial rather than a number in a box: the arc is the evidence closing, and
 * the gap that stays open is the part of the case Worth could not make. Drawn
 * as SVG so it stays crisp at any size, and animated on `stroke-dashoffset`,
 * which does not trigger layout.
 */
function ScoreRing({ score, settled }: { score: number; settled: boolean }) {
  const R = 52
  const C = 2 * Math.PI * R
  /* Three quarters of a turn, so the dial has a visible start and end. */
  const SWEEP = 0.75
  const filled = C * SWEEP * (score / 100)

  return (
    <div className="relative">
      <svg viewBox="0 0 128 128" className="size-[9.5rem] -rotate-[225deg] sm:size-[11rem]">
        <circle
          cx="64"
          cy="64"
          r={R}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={`${C * SWEEP} ${C}`}
        />
        <circle
          cx="64"
          cy="64"
          r={R}
          fill="none"
          stroke="url(#worth-dial)"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${C}`}
          className="transition-[stroke-dasharray] duration-300 ease-out motion-reduce:transition-none"
        />
        <defs>
          <linearGradient id="worth-dial" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--color-electric)" />
            <stop offset="100%" stopColor="var(--color-think-lift)" />
          </linearGradient>
        </defs>
      </svg>

      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="tnum text-[3rem] leading-none font-semibold tracking-[-0.05em] text-white sm:text-[3.5rem]">
          {score}
        </span>
        <span
          className={cn(
            'label mt-1.5 transition-colors duration-500',
            settled ? 'text-white/40' : 'text-white/20',
          )}
        >
          out of 100
        </span>
      </div>
    </div>
  )
}
