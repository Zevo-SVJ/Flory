'use client'

import { useEffect, useState } from 'react'
import { ProductImage } from './product-image'
import { cn } from '@/lib/utils/cn'

/**
 * The hero's product demonstration.
 *
 * A real product sitting on a violet-lit stage with Worth's findings landing
 * around it one at a time, then resolving into a score, a verdict and a price
 * drop. It runs once on mount and stays resolved — a loop would turn the page's
 * most important explanation into wallpaper.
 *
 * The motion is not an "AI scanning" effect. Each fragment is one of the real
 * dimensions Worth checks, carrying the actual finding that drives the verdict,
 * so by the end the visitor has watched a price get beaten and a conclusion
 * reached. That is the whole product, explained without a line of marketing.
 *
 * Under prefers-reduced-motion it renders the finished state immediately.
 */

interface Fragment {
  label: string
  value: string
  note?: string
  tone: 'positive' | 'negative' | 'neutral'
  /** Placement on the desktop stage. Mobile stacks them in a row instead. */
  place: string
}

const FRAGMENTS: Fragment[] = [
  {
    label: 'Price',
    value: '€399',
    note: 'here',
    tone: 'negative',
    place: 'left-0 top-[2%]',
  },
  {
    label: 'Better price',
    value: '€329',
    note: 'verified retailer',
    tone: 'positive',
    place: 'right-0 top-[16%]',
  },
  {
    label: 'Reviews',
    value: 'Mostly positive',
    note: '2,140 read',
    tone: 'positive',
    place: 'left-0 bottom-[8%]',
  },
  {
    label: 'Trust',
    value: 'Verified seller',
    note: '2-year warranty',
    tone: 'neutral',
    place: 'right-0 bottom-[0%]',
  },
]

const DOT = {
  positive: 'bg-buy-lift',
  negative: 'bg-skip-lift',
  neutral: 'bg-white/40',
} as const

export function ProductAnalysis({ className }: { className?: string }) {
  const [stage, setStage] = useState(-1)
  const resolved = stage >= FRAGMENTS.length

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      const skip = window.setTimeout(() => setStage(FRAGMENTS.length), 0)
      return () => window.clearTimeout(skip)
    }
    const timers = [
      ...FRAGMENTS.map((_, i) => window.setTimeout(() => setStage(i), 560 + i * 420)),
      window.setTimeout(() => setStage(FRAGMENTS.length), 560 + FRAGMENTS.length * 420),
    ]
    return () => timers.forEach(window.clearTimeout)
  }, [])

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      {/* The stage. */}
      <div className="stage-light rounded-stage border-midnight-line bg-midnight relative overflow-hidden border px-5 pt-6 pb-5 sm:px-7 sm:pb-7">
        <div className="flex items-center justify-between gap-3">
          <span className="label text-white/45">Analysing</span>
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

        {/* Product + surrounding findings. */}
        <div className="relative mt-4 sm:mt-6">
          {/* Desktop: findings float around the product. */}
          <div className="relative mx-auto hidden aspect-[6/5] w-full lg:block">
            {/* The product owns the centre column; fragments live in the
                margins either side so nothing ever covers it. */}
            <div className="absolute inset-y-[2%] right-[23%] left-[23%] flex items-center justify-center">
              <ProductImage
                asset="headphones"
                priority
                sizes="(max-width: 1024px) 60vw, 320px"
                className="h-full w-full drop-shadow-[0_28px_50px_rgba(0,0,0,0.55)]"
              />
            </div>
            {FRAGMENTS.map((fragment, index) => (
              <div
                key={fragment.label}
                className={cn('absolute w-[9.25rem] xl:w-[10rem]', fragment.place)}
              >
                {stage >= index && <FragmentChip fragment={fragment} className="anim-land" />}
              </div>
            ))}
          </div>

          {/* Mobile / tablet: product above, findings in a tight list beneath.
              Floating them on a phone would either overlap the product or
              shrink it to nothing. */}
          <div className="lg:hidden">
            <div className="mx-auto aspect-[4/3] w-full max-w-[18rem]">
              <ProductImage
                asset="headphones"
                priority
                sizes="60vw"
                className="h-full w-full drop-shadow-[0_22px_40px_rgba(0,0,0,0.5)]"
              />
            </div>
            <div className="mt-5 grid grid-cols-2 gap-2">
              {FRAGMENTS.map((fragment, index) => (
                <div key={fragment.label}>
                  {stage >= index && <FragmentChip fragment={fragment} className="anim-land" />}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* The conclusion. */}
        <div
          className={cn(
            'border-midnight-line mt-5 border-t pt-5 transition-opacity duration-500 sm:mt-6 sm:pt-6',
            'motion-reduce:transition-none',
            resolved ? 'opacity-100' : 'opacity-0',
          )}
          aria-live="polite"
        >
          {resolved && (
            <div className="anim-settle flex flex-col gap-4">
              <div className="flex items-end justify-between gap-4">
                <div>
                  <span className="label text-white/45">Worth verdict</span>
                  <p className="text-think-lift mt-2 text-2xl leading-none font-semibold tracking-[-0.02em] uppercase sm:text-[1.75rem]">
                    Think twice
                  </p>
                </div>
                <div className="flex items-end gap-1.5">
                  <span className="tnum text-[3.25rem] leading-[0.82] font-semibold tracking-[-0.055em] text-white sm:text-[3.75rem]">
                    61
                  </span>
                  <span className="tnum pb-1.5 text-xs font-medium text-white/40">/100</span>
                </div>
              </div>

              <p className="font-serif text-lg leading-snug text-white sm:text-xl">
                The product is good. The price isn’t.
              </p>

              <div className="border-midnight-line flex flex-wrap items-baseline gap-x-3 gap-y-2 border-t pt-4">
                <span className="tnum text-lg font-medium text-white/35 line-through decoration-1">
                  €399
                </span>
                <ArrowRight />
                <span className="tnum text-2xl font-semibold tracking-[-0.03em] text-white">
                  €329
                </span>
                <span className="tnum bg-buy-lift/15 text-buy-lift rounded-full px-2.5 py-1 text-[0.8125rem] font-semibold">
                  Save €70
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      <p className="text-graphite px-1 text-center text-[0.75rem] lg:text-left">
        Illustrative analysis — Worth’s research engine isn’t connected yet.
      </p>
    </div>
  )
}

function FragmentChip({ fragment, className }: { fragment: Fragment; className?: string }) {
  return (
    <div
      className={cn(
        'rounded-xl border border-white/10 bg-white/[0.07] px-3 py-2.5 backdrop-blur-md',
        className,
      )}
    >
      <div className="flex items-center gap-1.5">
        <span className={cn('size-1.5 shrink-0 rounded-full', DOT[fragment.tone])} aria-hidden />
        <span className="label text-white/45">{fragment.label}</span>
      </div>
      <p className="tnum mt-1.5 text-[0.9375rem] leading-tight font-semibold text-white">
        {fragment.value}
      </p>
      {fragment.note && <p className="text-[0.75rem] text-white/40">{fragment.note}</p>}
    </div>
  )
}

/** The Worth arrow: squared head, violet. Repeated wherever a number moves. */
function ArrowRight() {
  return (
    <svg
      width="22"
      height="12"
      viewBox="0 0 22 12"
      fill="none"
      aria-hidden
      className="shrink-0 self-center"
    >
      <path
        d="M0 6h19M14.5 1.5 19.5 6l-5 4.5"
        stroke="var(--color-violet-lift)"
        strokeWidth="1.75"
        strokeLinecap="square"
      />
    </svg>
  )
}
