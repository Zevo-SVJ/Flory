'use client'

import { useEffect, useState } from 'react'
import { ProductImage } from './product-image'
import { cn } from '@/lib/utils/cn'

/**
 * The hero's product investigation.
 *
 * One object, read top to bottom, that tells the whole story in three beats:
 *
 *   PRODUCT  — a real photograph, with the listing's own name and price
 *              attached to it, so the first thing understood is "this is the
 *              thing being judged".
 *   INVESTIGATION — Worth's four checks running over that product. A scan
 *              passes across the photograph while they resolve, and a spine
 *              connects the product to the findings and the findings to the
 *              conclusion, so the interface reads as inspecting the object
 *              rather than sitting next to it.
 *   VERDICT  — the score, the call, the sentence, and the money.
 *
 * The same object is used at every width. The photograph's crop and the type
 * scale change, but the narrative order never does — a phone gets the
 * identical three beats at a size where the product is still unmistakably a
 * pair of headphones.
 *
 * The motion is the investigation, not decoration: nothing spins, nothing
 * sparkles, and no element fades in merely because it exists. It runs once on
 * mount and stays resolved — a loop would turn the page's most important
 * explanation into wallpaper. Under prefers-reduced-motion the finished state
 * renders immediately.
 *
 * Every value here is illustrative. See `PRODUCT_EXAMPLE` and the disclosure
 * rendered directly beneath the stage.
 */

/* ---------------------------------------------------------------------------
 * Illustrative data
 *
 * Deliberately an unbranded product. Worth's research engine is not connected
 * yet, so this verdict is authored, not measured — and publishing an authored
 * verdict against a named, identifiable product would be a claim about a real
 * company's goods that Worth has not earned the right to make.
 * ------------------------------------------------------------------------ */

const PRODUCT_EXAMPLE = {
  name: 'Over-ear noise-cancelling headphones',
  seller: 'Audio Store',
  listed: '€399',
  best: '€329',
  saving: '€70',
  score: 61,
  verdict: 'Think twice',
  line: 'The product is good. The price isn’t.',
} as const

interface Check {
  label: string
  finding: string
  tone: 'positive' | 'negative' | 'neutral'
}

const CHECKS: Check[] = [
  { label: 'Price', finding: '€399 here', tone: 'negative' },
  { label: 'Reviews', finding: '4.4 · 2,140 ratings', tone: 'positive' },
  { label: 'Trust', finding: 'Verified · 2-yr warranty', tone: 'neutral' },
  { label: 'Alternatives', finding: '€329 elsewhere', tone: 'positive' },
]

const TONE_TICK = {
  positive: 'text-buy-lift',
  negative: 'text-skip-lift',
  neutral: 'text-white/55',
} as const

/* ---------------------------------------------------------------------------
 * Timeline
 *
 * Step by step, in milliseconds from mount. Elegant and fast: the whole
 * investigation is over in about two and a half seconds, which is short enough
 * that a visitor who scrolls straight past has still seen a verdict land.
 * ------------------------------------------------------------------------ */

const STEP_PRODUCT = 1
const STEP_IDENTITY = 2
const STEP_SCANNING = 3
const STEP_FIRST_CHECK = 4
const STEP_VERDICT = STEP_FIRST_CHECK + CHECKS.length
const STEP_MONEY = STEP_VERDICT + 1
const LAST_STEP = STEP_MONEY

const TIMELINE = [
  60, // product plate
  420, // name + price
  700, // scan begins
  980, // price
  1240, // reviews
  1500, // trust
  1760, // alternatives
  2020, // verdict
  2320, // money
]

export function ProductAnalysis({ className }: { className?: string }) {
  const [step, setStep] = useState(0)
  const [score, setScore] = useState(0)

  const scanning = step >= STEP_SCANNING && step < STEP_VERDICT
  const resolved = step >= STEP_VERDICT
  const checksDone = Math.max(0, Math.min(step - STEP_FIRST_CHECK + 1, CHECKS.length))

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      const skip = window.setTimeout(() => {
        setStep(LAST_STEP)
        setScore(PRODUCT_EXAMPLE.score)
      }, 0)
      return () => window.clearTimeout(skip)
    }
    const timers = TIMELINE.map((at, index) => window.setTimeout(() => setStep(index + 1), at))
    return () => timers.forEach(window.clearTimeout)
  }, [])

  /* The score counts up once the verdict lands. It is the one number the
     visitor is being asked to trust, so it arrives by settling on a value
     rather than simply appearing. */
  useEffect(() => {
    if (step < STEP_VERDICT || score >= PRODUCT_EXAMPLE.score) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      const skip = window.setTimeout(() => setScore(PRODUCT_EXAMPLE.score), 0)
      return () => window.clearTimeout(skip)
    }
    const tick = window.setInterval(() => {
      setScore((current) => Math.min(current + 3, PRODUCT_EXAMPLE.score))
    }, 22)
    return () => window.clearInterval(tick)
  }, [step, score])

  return (
    <div className={cn('flex flex-col gap-3', className)}>
      <div className="stage-light rounded-stage border-midnight-line bg-midnight relative overflow-hidden border p-4 sm:p-5">
        {/* ── Beat 0: who is doing the looking ─────────────────────────── */}
        <div className="flex items-center justify-between gap-3">
          <span className="label text-white/45">Worth is analysing</span>
          <span
            className={cn(
              'flex items-center gap-1.5 text-[0.6875rem] font-medium',
              resolved ? 'text-buy-lift' : 'text-violet-lift',
            )}
          >
            <span
              className={cn(
                'size-1.5 rounded-full',
                resolved ? 'bg-buy-lift' : 'bg-violet-lift animate-pulse',
              )}
            />
            {resolved ? 'Done' : 'Checking'}
          </span>
        </div>

        {/* ── Beat 1: the product ──────────────────────────────────────── */}
        <div
          className={cn(
            'relative mt-3 overflow-hidden rounded-xl border border-white/10',
            step >= STEP_PRODUCT ? 'anim-settle' : 'invisible',
          )}
        >
          <ProductImage
            asset="headphones"
            priority
            sizes="(max-width: 640px) 92vw, (max-width: 1024px) 60vw, 460px"
            className="aspect-[4/3] w-full sm:aspect-[16/10]"
          />

          {/* The inspection pass: a single beam travelling down the product
              while the checks resolve. It is the visual link between "Worth is
              looking" and "here is what Worth found". */}
          {scanning && (
            <div aria-hidden className="anim-scan pointer-events-none absolute inset-0" />
          )}

          {/* The listing's own identity, attached to the product rather than
              floating beside it. */}
          <div
            className={cn(
              'absolute inset-x-0 bottom-0 flex items-end justify-between gap-3 bg-gradient-to-t from-black/85 via-black/55 to-transparent px-3.5 pt-10 pb-3',
              step >= STEP_IDENTITY ? 'anim-land' : 'invisible',
            )}
          >
            <div className="min-w-0">
              <p className="line-clamp-2 text-[0.8125rem] leading-snug font-medium text-white sm:text-[0.875rem]">
                {PRODUCT_EXAMPLE.name}
              </p>
              <p className="mt-0.5 text-[0.75rem] text-white/55">{PRODUCT_EXAMPLE.seller}</p>
            </div>
            <div className="shrink-0 text-right">
              <p className="label text-white/45">Listed</p>
              <p className="tnum mt-1 text-[1.0625rem] leading-none font-semibold text-white">
                {PRODUCT_EXAMPLE.listed}
              </p>
            </div>
          </div>
        </div>

        {/* The spine. It runs product → findings → verdict, and only lights up
            as far as the investigation has actually got. */}
        <Spine active={step >= STEP_SCANNING} />

        {/* ── Beat 2: the investigation ────────────────────────────────── */}
        <ul className="grid grid-cols-2 gap-1.5">
          {CHECKS.map((check, index) => {
            const done = index < checksDone
            return (
              <li
                key={check.label}
                className={cn(
                  'rounded-lg border px-2.5 py-2 transition-colors duration-300',
                  done
                    ? 'border-midnight-line bg-midnight-2 anim-land'
                    : 'border-white/[0.06] bg-white/[0.02]',
                )}
              >
                <div className="flex items-center justify-between gap-1.5">
                  <span className={cn('label truncate', done ? 'text-white/45' : 'text-white/25')}>
                    {check.label}
                  </span>
                  <span
                    aria-hidden
                    className={cn(
                      'shrink-0 text-[0.6875rem] leading-none',
                      done ? TONE_TICK[check.tone] : 'text-white/15',
                    )}
                  >
                    {done ? '✓' : '·'}
                  </span>
                </div>
                <p
                  className={cn(
                    'mt-1 text-[0.75rem] leading-tight sm:text-[0.8125rem]',
                    done ? 'text-white/85' : 'text-white/15',
                  )}
                >
                  {done ? check.finding : '—'}
                </p>
              </li>
            )
          })}
        </ul>

        <Spine active={resolved} />

        {/* ── Beat 3: the verdict ──────────────────────────────────────────
            Rendered from the start, in a pending state. Its space is where the
            conclusion will be, and leaving that space blank for two seconds
            reads as a broken card rather than as work in progress. */}
        <div>
          <div className="flex items-end justify-between gap-4">
            <div className="min-w-0">
              <p className="label text-white/45">Worth verdict</p>
              <p
                className={cn(
                  'mt-2 text-[1.375rem] leading-none font-semibold tracking-[-0.02em] sm:text-[1.5rem]',
                  resolved ? 'text-think-lift anim-land' : 'text-white/20',
                )}
              >
                {resolved ? PRODUCT_EXAMPLE.verdict : 'Pending'}
              </p>
            </div>
            <p className="tnum flex shrink-0 items-baseline gap-1 text-white">
              <span
                className={cn(
                  'font-semibold tracking-[-0.04em]',
                  resolved
                    ? 'text-[2.5rem] leading-none sm:text-[2.75rem]'
                    : /* the placeholder is a mark, not a number: at score size a
                         dash reads as a loading bar */
                      'text-[1.75rem] leading-[2.5rem] text-white/20 sm:leading-[2.75rem]',
                )}
              >
                {resolved ? score : '—'}
              </span>
              <span className={cn('text-[0.8125rem]', resolved ? 'text-white/40' : 'text-white/20')}>
                /100
              </span>
            </p>
          </div>

          {/* The score as a position rather than a number alone: it is the
              conclusion of the four checks above, so it gets a scale. */}
          <div
            aria-hidden
            className="bg-midnight-3 relative mt-3 h-1 w-full overflow-hidden rounded-full"
          >
            <div
              className="bg-think-lift h-full rounded-full transition-[width] duration-700 ease-out motion-reduce:transition-none"
              style={{ width: `${score}%` }}
            />
          </div>

          <p
            className={cn(
              'mt-3 font-serif text-[1.0625rem] leading-snug text-white/90 sm:text-[1.125rem]',
              resolved ? 'anim-land' : 'invisible',
            )}
          >
            {PRODUCT_EXAMPLE.line}
          </p>

          {/* The money. The point of the whole object. */}
          <div
            className={cn(
              'border-midnight-line mt-3.5 flex flex-wrap items-center gap-x-3 gap-y-2 border-t pt-3.5',
              step >= STEP_MONEY ? 'anim-land' : 'invisible',
            )}
          >
            <span className="tnum text-[0.9375rem] text-white/35 line-through">
              {PRODUCT_EXAMPLE.listed}
            </span>
            <span aria-hidden className="text-violet-lift text-[0.9375rem]">
              →
            </span>
            <span className="tnum text-[1.375rem] leading-none font-semibold tracking-[-0.03em] text-white">
              {PRODUCT_EXAMPLE.best}
            </span>
            <span className="bg-buy/25 text-buy-lift ml-auto rounded-full px-2.5 py-1 text-[0.75rem] font-medium">
              Save {PRODUCT_EXAMPLE.saving}
            </span>
          </div>
        </div>
      </div>

      <p className="text-faint px-1 text-[0.75rem]">
        Illustrative example — Worth’s research engine isn’t connected yet, so this verdict is
        written, not researched.
      </p>
    </div>
  )
}

/**
 * The connector between beats. A short vertical rule with a node on it, so the
 * three parts of the stage read as one flow instead of three stacked cards.
 */
function Spine({ active }: { active: boolean }) {
  return (
    <div aria-hidden className="flex h-6 items-center justify-center">
      <span
        className={cn(
          'relative h-full w-px transition-colors duration-500',
          active ? 'bg-violet/70' : 'bg-white/10',
        )}
      >
        <span
          className={cn(
            'absolute top-1/2 left-1/2 size-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full transition-colors duration-500',
            active ? 'bg-violet-lift' : 'bg-white/15',
          )}
        />
      </span>
    </div>
  )
}
