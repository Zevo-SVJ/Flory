'use client'

import { useEffect, useState } from 'react'
import { PRIMARY_EXAMPLE } from '@/lib/analysis/fixtures'
import { VERDICT_LABEL } from '@/lib/analysis/verdict'
import { ScoreMeter } from './score-meter'
import { PriceDrop } from './price-drop'
import { cn } from '@/lib/utils/cn'

/**
 * The hero's product visualisation.
 *
 * Worth carrying out an investigation and reaching a conclusion. It runs once
 * on mount, then stays resolved — a loop would turn the page's most important
 * explanation into wallpaper.
 *
 * The motion is not decoration and not a fake AI shimmer: each row is one of
 * the six real dimensions, and each resolves into the actual finding that
 * drives the verdict. By the end the visitor has watched Worth check a price,
 * find a cheaper listing, and conclude "think twice" — which is the entire
 * product explained without a sentence of marketing copy.
 *
 * Under prefers-reduced-motion it renders the finished state immediately.
 */

const CHECKS = [
  { label: 'Price', finding: 'Advertised €892', tone: 'caution' as const },
  { label: 'Reviews', finding: '1,284 read · support praised', tone: 'positive' as const },
  { label: 'Trust', finding: 'Authorised seller · 30-day returns', tone: 'positive' as const },
  { label: 'Alternatives', finding: 'Equivalent plan for €724', tone: 'positive' as const },
]

const TONE_DOT = {
  positive: 'bg-buy',
  negative: 'bg-skip',
  caution: 'bg-think',
} as const

export function LiveAnalysis({ className }: { className?: string }) {
  // -1 = nothing checked yet; CHECKS.length = resolved.
  const [stage, setStage] = useState(-1)
  const resolved = stage >= CHECKS.length

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      const skip = window.setTimeout(() => setStage(CHECKS.length), 0)
      return () => window.clearTimeout(skip)
    }
    const timers = [
      ...CHECKS.map((_, i) => window.setTimeout(() => setStage(i), 520 + i * 460)),
      window.setTimeout(() => setStage(CHECKS.length), 520 + CHECKS.length * 460),
    ]
    return () => timers.forEach(window.clearTimeout)
  }, [])

  return (
    <div
      className={cn(
        'rounded-object border-line bg-surface shadow-object overflow-hidden border',
        className,
      )}
    >
      {/* What's being checked. */}
      <div className="border-line flex items-center gap-3.5 border-b p-4 sm:p-5">
        <ProductTile />
        <div className="min-w-0 flex-1">
          <p className="label text-graphite">Analysing</p>
          <p className="text-ink mt-1.5 truncate font-medium">{PRIMARY_EXAMPLE.title}</p>
        </div>
        <span className="tnum text-ink shrink-0 text-lg font-semibold sm:text-xl">€1,007</span>
      </div>

      {/* The investigation. */}
      <ul className="divide-line divide-y">
        {CHECKS.map((check, index) => {
          const done = stage >= index
          const active = stage === index - 1 || (stage === -1 && index === 0)
          return (
            <li
              key={check.label}
              className="relative flex items-center gap-3 overflow-hidden px-4 py-2.5 sm:px-5"
            >
              <span className="label text-graphite w-[5.75rem] shrink-0 sm:w-24">
                {check.label}
              </span>

              {done ? (
                <span
                  className="anim-check flex min-w-0 flex-1 items-center gap-2"
                  style={{ animationDelay: '0ms' }}
                >
                  <span className={cn('size-1.5 shrink-0 rounded-full', TONE_DOT[check.tone])} />
                  <span className="text-ink-soft truncate text-[0.8125rem] sm:text-sm">
                    {check.finding}
                  </span>
                </span>
              ) : (
                <span className="relative min-w-0 flex-1 overflow-hidden">
                  <span
                    className={cn(
                      'bg-paper-2 relative block h-2 w-full max-w-[11rem] overflow-hidden rounded-full',
                      active && 'anim-scan',
                    )}
                  />
                </span>
              )}
            </li>
          )
        })}
      </ul>

      {/* The conclusion. */}
      <div
        className={cn(
          'border-line bg-paper/60 border-t p-4 transition-opacity duration-500 sm:p-5',
          'motion-reduce:transition-none',
          resolved ? 'opacity-100' : 'opacity-0',
        )}
        aria-live="polite"
      >
        {resolved && (
          <div className="anim-settle flex flex-col gap-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="label text-graphite">Worth verdict</p>
                <p className="text-think mt-2 text-2xl leading-none font-semibold tracking-[-0.02em] uppercase sm:text-[1.75rem]">
                  {VERDICT_LABEL.think_twice}
                </p>
              </div>
              <div className="flex items-end gap-1.5">
                <span className="tnum text-think text-[2.75rem] leading-[0.84] font-semibold tracking-[-0.05em] sm:text-[3.25rem]">
                  61
                </span>
                <span className="tnum text-faint pb-1 text-xs font-medium">/100</span>
              </div>
            </div>

            <ScoreMeter score={61} verdict="think_twice" size="sm" showScore={false} />

            <p className="text-ink font-serif text-[1.0625rem] leading-snug sm:text-lg">
              {PRIMARY_EXAMPLE.summary}
            </p>

            <div className="border-line border-t pt-3.5">
              <PriceDrop from="€1,007" to="€724" saving="€283" size="sm" />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Abstract product mark. Not stock imagery and not a photo we don't have —
 * a drawn glyph that reads as "the thing being checked".
 */
function ProductTile() {
  return (
    <span className="rounded-note border-line bg-paper flex size-11 shrink-0 items-center justify-center border sm:size-12">
      <svg
        width="22"
        height="22"
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden
        className="text-ink-soft"
      >
        <path
          d="M4 14v-2a8 8 0 0 1 16 0v2"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
        <rect
          x="2.5"
          y="13.5"
          width="4.5"
          height="7"
          rx="1.6"
          stroke="currentColor"
          strokeWidth="1.6"
        />
        <rect
          x="17"
          y="13.5"
          width="4.5"
          height="7"
          rx="1.6"
          stroke="currentColor"
          strokeWidth="1.6"
        />
      </svg>
    </span>
  )
}
