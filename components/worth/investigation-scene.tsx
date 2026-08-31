'use client'

import { useEffect, useState } from 'react'
import { CheckoutSurface } from './checkout-surface'
import { MONEY_EXAMPLE } from '@/lib/analysis/fixtures'
import { cn } from '@/lib/utils/cn'

/**
 * The hero scene: a decision being made.
 *
 * The subject is a checkout, because that is the moment Worth exists for. It
 * is not a photograph of a product and not a dashboard — it is the screen you
 * are looking at with your card in your hand.
 *
 * The sequence is the argument, in this order and no other:
 *
 *   1  the checkout stands there, at its advertised price
 *   2  Worth starts reading it
 *   3  the fees Worth found appear *on the checkout*, and the total climbs
 *   4  the six dimensions resolve around it, one at a time
 *   5  the score counts up
 *   6  the verdict lands, last
 *
 * That is question → investigation → answer, and nothing animates that is not
 * one of those beats. Under prefers-reduced-motion the finished state renders
 * immediately with no transforms at all.
 *
 * Every figure is illustrative — Worth's research engine is not connected, so
 * this verdict is authored. The checkout is deliberately unbranded.
 */

const CHECKOUT_LINES = [
  { label: MONEY_EXAMPLE.base.label, amount: MONEY_EXAMPLE.base.amount },
  ...MONEY_EXAMPLE.additions.map((a) => ({ label: a.label, amount: `+ ${a.amount}`, late: true })),
]

interface Dimension {
  label: string
  finding: string
  tone: 'positive' | 'caution' | 'negative'
  /** Where it enters from, so evidence converges rather than fading up. */
  from: string
}

const DIMENSIONS: Dimension[] = [
  { label: 'Price', finding: 'Advertised €892', tone: 'caution', from: '-18px,-10px' },
  { label: 'Fees', finding: '€115 added at checkout', tone: 'negative', from: '18px,-10px' },
  { label: 'Reviews', finding: '4.5 · 1,284 reviews', tone: 'positive', from: '-20px,0px' },
  { label: 'Trust', finding: 'Established seller', tone: 'positive', from: '20px,0px' },
  { label: 'Risk', finding: 'Locked in after 14 days', tone: 'negative', from: '-18px,10px' },
  { label: 'Alternatives', finding: '€724, cancel any time', tone: 'positive', from: '18px,10px' },
]

const TONE = {
  positive: 'text-buy-lift',
  caution: 'text-think-lift',
  negative: 'text-skip-lift',
} as const

const STEP_READING = 1
const STEP_FEES = 2
const STEP_FIRST_DIM = 3
const STEP_SCORE = STEP_FIRST_DIM + DIMENSIONS.length
const STEP_VERDICT = STEP_SCORE + 1
const STEP_MONEY = STEP_VERDICT + 1

/* ms from mount, one entry per step, ending on STEP_MONEY. The whole thing
   resolves inside three seconds. */
const TIMELINE = [
  400, // 1  Worth starts reading
  900, // 2  the fees appear and the total climbs
  1250, // 3  price
  1400, // 4  fees
  1550, // 5  reviews
  1700, // 6  trust
  1850, // 7  risk
  2000, // 8  alternatives
  2250, // 9  the score counts up
  2550, // 10 the verdict
  2850, // 11 the money
]

/* The timeline must reach the last step or the final beat never renders. */
if (TIMELINE.length !== STEP_MONEY) {
  throw new Error(
    `InvestigationScene timeline has ${TIMELINE.length} steps but needs ${STEP_MONEY}`,
  )
}

const SCORE = 68

export function InvestigationScene({ className }: { className?: string }) {
  const [step, setStep] = useState(0)
  const [score, setScore] = useState(0)
  const [still, setStill] = useState(false)

  const reading = step >= STEP_READING && step < STEP_SCORE
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
    if (step < STEP_SCORE || score >= SCORE || still) return
    const tick = window.setInterval(() => setScore((c) => Math.min(c + 4, SCORE)), 18)
    return () => window.clearInterval(tick)
  }, [step, score, still])

  return (
    <div className={cn('relative', className)}>
      <div className="mx-auto grid w-full max-w-5xl grid-cols-1 items-start gap-12 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:gap-14">
        {/* The thing being decided. */}
        <div className="relative mx-auto w-full max-w-[24rem] lg:mx-0">
          <CheckoutSurface
            tone="dark"
            lines={CHECKOUT_LINES}
            total={step >= STEP_FEES ? MONEY_EXAMPLE.actual.amount : MONEY_EXAMPLE.base.amount}
            showLate={step >= STEP_FEES}
          />

          {/* Worth reading it. One pass, then it stops. */}
          {reading && !still && (
            <div
              aria-hidden
              className="rounded-object anim-scan pointer-events-none absolute inset-0 overflow-hidden"
            />
          )}

          <p
            className={cn(
              'mt-4 flex items-center justify-center gap-2 text-[0.8125rem] font-medium',
              resolved ? 'text-buy-lift' : 'text-violet-lift',
            )}
          >
            <span
              className={cn(
                'size-1.5 rounded-full',
                resolved ? 'bg-buy-lift' : 'bg-violet-lift motion-safe:animate-pulse',
              )}
            />
            {resolved ? 'Worth has an answer' : 'Worth is reading this checkout'}
          </p>
        </div>

        {/* What Worth found, and what it concluded. */}
        <div>
          <ul className="stagger grid grid-cols-2 gap-x-6 gap-y-4 sm:gap-x-10">
            {DIMENSIONS.map((d, i) => (
              <li
                key={d.label}
                style={
                  {
                    '--i': i,
                    '--from-x': d.from.split(',')[0],
                    '--from-y': d.from.split(',')[1],
                  } as React.CSSProperties
                }
                className={cn(
                  'border-t border-white/12 pt-3',
                  i < dimsDone ? 'motion-safe:anim-converge' : 'invisible',
                )}
              >
                <p className="label text-white/40">{d.label}</p>
                <p className={cn('mt-1.5 text-[0.9375rem] leading-snug', TONE[d.tone])}>
                  {d.finding}
                </p>
              </li>
            ))}
          </ul>

          {/* The conclusion. */}
          <div className="mt-10 border-t border-white/12 pt-8">
            <p className="tnum flex items-start text-white">
              <span className="text-display font-semibold">{step >= STEP_SCORE ? score : 0}</span>
              <span className="mt-3 ml-1.5 text-[1rem] text-white/35 sm:mt-5 sm:text-[1.25rem]">
                /100
              </span>
            </p>

            <p
              className={cn(
                'text-think-lift text-statement mt-1 font-serif font-medium',
                resolved ? 'motion-safe:anim-wipe' : 'invisible',
              )}
            >
              Think twice
            </p>

            <p
              className={cn(
                'text-lead mt-5 max-w-[30ch] text-white/60',
                resolved ? 'motion-safe:anim-land' : 'invisible',
              )}
            >
              The deal looks good at first. The actual cost changes the picture.
            </p>

            <div
              className={cn(
                'mt-7 flex flex-wrap items-center gap-x-4 gap-y-3',
                step >= STEP_MONEY ? 'motion-safe:anim-land' : 'invisible',
              )}
            >
              <span className="tnum text-figure-sm text-white/25 line-through">
                {MONEY_EXAMPLE.actual.amount}
              </span>
              <span aria-hidden className="text-violet-lift text-xl">
                →
              </span>
              <span className="tnum text-figure-sm font-semibold text-white">
                {MONEY_EXAMPLE.better.amount}
              </span>
              <span className="bg-buy/25 text-buy-lift rounded-full px-3 py-1.5 text-[0.8125rem] font-medium whitespace-nowrap">
                {MONEY_EXAMPLE.saving} less
              </span>
            </div>
          </div>
        </div>
      </div>

      <p className="mx-auto mt-12 max-w-5xl text-[0.8125rem] text-white/45">
        Illustrative example. Worth’s research engine isn’t connected yet, so this checkout, these
        figures and this verdict are written, not researched.
      </p>
    </div>
  )
}
