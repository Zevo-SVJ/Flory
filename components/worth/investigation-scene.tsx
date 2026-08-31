'use client'

import { useEffect, useState } from 'react'
import Image from 'next/image'
import { PRODUCT_ASSETS } from '@/lib/product-assets'
import { cn } from '@/lib/utils/cn'

/**
 * The hero scene: Worth investigating a product.
 *
 * This is a scene, not a card. The product photograph fills the frame, the
 * evidence sits *on* it at different depths and scales, and the verdict breaks
 * out of the bottom edge at display size. Nothing here is boxed, because the
 * point is that the visitor is looking at a real object being examined, not at
 * a dashboard that happens to mention one.
 *
 * Depth is built from four layers:
 *   0  the lit set        — the photograph, plus the section's own violet pool
 *   1  the inspection     — a beam that passes over the product while checking
 *   2  the evidence       — small, blurred-backed facts pinned around the product
 *   3  the verdict        — the largest type on the page, overlapping the photo
 *
 * The motion is the investigation: the product is already there, the facts
 * land on it one at a time, and the score resolves last. It runs once.
 * Reduced motion renders the finished state.
 *
 * Everything is illustrative. Worth's research engine is not connected, so
 * this verdict is authored — and the product is deliberately unbranded, since
 * an authored verdict against an identifiable brand would be a claim about a
 * real company's goods that Worth has not earned the right to make.
 */

const EXAMPLE = {
  name: 'Over-ear noise-cancelling headphones',
  listed: '€399',
  best: '€329',
  saving: '€70',
  score: 61,
  verdict: 'Think twice',
  line: 'The product is good. The price isn’t.',
} as const

interface Fact {
  label: string
  value: string
  tone: 'positive' | 'negative' | 'neutral'
  /** Where it pins over the photograph. Mobile and desktop differ in scale. */
  place: string
}

/* All four pin inside the top two thirds of the plate. The verdict overlaps
   the bottom third, and a price floating behind the score would read as a
   rendering fault rather than as depth. */
const FACTS: Fact[] = [
  { label: 'Listed here', value: '€399', tone: 'negative', place: 'top-[5%] left-[5%] sm:left-[8%]' },
  { label: 'Reviews', value: '4.4 ★', tone: 'positive', place: 'top-[16%] right-[5%] sm:right-[8%]' },
  { label: 'Seller', value: 'Verified', tone: 'neutral', place: 'top-[40%] left-[5%] sm:left-[8%]' },
  { label: 'Found elsewhere', value: '€329', tone: 'positive', place: 'top-[52%] right-[5%] sm:right-[8%]' },
]

const TONE = {
  positive: 'text-buy-lift',
  negative: 'text-skip-lift',
  neutral: 'text-white/70',
} as const

const STEP_SCAN = 1
const STEP_FIRST_FACT = 2
const STEP_VERDICT = STEP_FIRST_FACT + FACTS.length
const STEP_MONEY = STEP_VERDICT + 1
const TIMELINE = [420, 720, 1000, 1280, 1560, 1860, 2180]

export function InvestigationScene({ className }: { className?: string }) {
  const [step, setStep] = useState(0)
  const [score, setScore] = useState(0)

  const scanning = step >= STEP_SCAN && step < STEP_VERDICT
  const resolved = step >= STEP_VERDICT
  const factsDone = Math.max(0, Math.min(step - STEP_FIRST_FACT + 1, FACTS.length))

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      const skip = window.setTimeout(() => {
        setStep(TIMELINE.length)
        setScore(EXAMPLE.score)
      }, 0)
      return () => window.clearTimeout(skip)
    }
    const timers = TIMELINE.map((at, i) => window.setTimeout(() => setStep(i + 1), at))
    return () => timers.forEach(window.clearTimeout)
  }, [])

  useEffect(() => {
    if (step < STEP_VERDICT || score >= EXAMPLE.score) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      const skip = window.setTimeout(() => setScore(EXAMPLE.score), 0)
      return () => window.clearTimeout(skip)
    }
    const tick = window.setInterval(() => {
      setScore((c) => Math.min(c + 3, EXAMPLE.score))
    }, 20)
    return () => window.clearInterval(tick)
  }, [step, score])

  const plate = PRODUCT_ASSETS.headphonesDark

  return (
    <div className={cn('relative', className)}>
      {/* Layer 0 — the set. Full-bleed photograph, no frame. */}
      <div className="relative mx-auto aspect-[4/3] w-full max-w-[46rem] sm:aspect-[16/10] lg:max-w-[64rem]">
        <Image
          src={plate.src}
          alt={plate.alt}
          fill
          priority
          sizes="(max-width: 640px) 100vw, (max-width: 1024px) 90vw, 1100px"
          /* Feathered with a mask rather than covered with gradient panels:
             the scene behind is lit unevenly, so painting the plate's edges a
             flat colour leaves a visible rectangle wherever the scene is
             lighter than the paint. A mask dissolves the photograph itself. */
          className="object-cover [mask-image:radial-gradient(56%_58%_at_50%_44%,#000_18%,transparent_100%)] [-webkit-mask-image:radial-gradient(56%_58%_at_50%_44%,#000_18%,transparent_100%)]"
        />

        {/* Layer 1 — the inspection pass. */}
        {scanning && (
          <div aria-hidden className="anim-scan pointer-events-none absolute inset-0" />
        )}

        {/* Layer 2 — evidence pinned to the object. */}
        {FACTS.map((fact, i) => (
          <div
            key={fact.label}
            className={cn(
              'fact absolute rounded-lg px-2.5 py-1.5 sm:px-3 sm:py-2',
              fact.place,
              i < factsDone ? 'anim-land' : 'invisible',
            )}
          >
            <p className="label text-[0.5625rem] text-white/50 sm:text-[0.625rem]">{fact.label}</p>
            <p
              className={cn(
                'tnum mt-1 text-[0.9375rem] leading-none font-semibold sm:text-[1.0625rem]',
                TONE[fact.tone],
              )}
            >
              {fact.value}
            </p>
          </div>
        ))}

      </div>

      {/* Layer 3 — the verdict, overlapping the photograph. */}
      <div className="relative z-10 -mt-[10%] px-5 sm:-mt-[9%] sm:px-8">
        <div className="mx-auto flex max-w-[42rem] flex-col items-center text-center">
          <p
            className={cn(
              'label text-white/45',
              resolved ? 'anim-land' : 'invisible',
            )}
          >
            Worth verdict
          </p>

          <p className="tnum on-photo mt-2 flex items-start justify-center text-white">
            <span className="text-display font-semibold">{resolved ? score : 0}</span>
            <span className="mt-3 ml-1 text-[1rem] text-white/40 sm:mt-5 sm:text-[1.25rem]">
              /100
            </span>
          </p>

          <p
            className={cn(
              'text-think-lift text-statement on-photo mt-1 font-serif font-medium',
              resolved ? 'anim-land' : 'invisible',
            )}
          >
            {EXAMPLE.verdict}
          </p>

          <p
            className={cn(
              'text-lead on-photo mt-4 max-w-[26ch] text-white/70',
              resolved ? 'anim-land' : 'invisible',
            )}
          >
            {EXAMPLE.line}
          </p>

          {/* The money. */}
          <div
            className={cn(
              'mt-7 flex items-center gap-3 sm:gap-4',
              step >= STEP_MONEY ? 'anim-land' : 'invisible',
            )}
          >
            <span className="tnum text-figure-sm text-white/25 line-through">{EXAMPLE.listed}</span>
            <span aria-hidden className="text-violet-lift text-xl">
              →
            </span>
            <span className="tnum text-figure-sm font-semibold text-white">{EXAMPLE.best}</span>
            <span className="bg-buy/25 text-buy-lift rounded-full px-3 py-1.5 text-[0.8125rem] font-medium whitespace-nowrap">
              Save {EXAMPLE.saving}
            </span>
          </div>

          <p className="mt-8 text-[0.75rem] text-white/30">
            Illustrative example. Worth’s research engine isn’t connected yet, so this verdict is
            written, not researched.
          </p>
        </div>
      </div>
    </div>
  )
}
