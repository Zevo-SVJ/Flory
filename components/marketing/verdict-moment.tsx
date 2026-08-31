'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { Disclosure } from './section'
import { PRIMARY_EXAMPLE } from '@/lib/analysis/fixtures'
import { cn } from '@/lib/utils/cn'

/**
 * Beat 03 — the verdict.
 *
 * An evidence field, not a list. The six dimensions sit around the score and
 * arrive from where they were found, one at a time; the number counts up only
 * once they are all in. That order is the whole claim: the verdict is what the
 * evidence adds up to, not a mood attached to it.
 *
 * The score is the largest thing on the page, and the verdict word lands after
 * it rather than with it, because the payoff is the conclusion — not the
 * arithmetic.
 */

const TONE = {
  positive: 'text-buy-lift',
  caution: 'text-think-lift',
  negative: 'text-skip-lift',
  neutral: 'text-white/60',
} as const

/* Where each dimension sits around the score on a wide screen, and where it
   travels in from. Two columns on a phone, in the same order. */
const PLACE = [
  'lg:col-start-1 lg:row-start-1',
  'lg:col-start-1 lg:row-start-2',
  'lg:col-start-1 lg:row-start-3',
  'lg:col-start-3 lg:row-start-1',
  'lg:col-start-3 lg:row-start-2',
  'lg:col-start-3 lg:row-start-3',
]

const FROM = ['-16px,-8px', '-20px,0px', '-16px,8px', '16px,-8px', '20px,0px', '16px,8px']

export function VerdictMoment() {
  const ref = useRef<HTMLElement>(null)
  const [shown, setShown] = useState(0)
  const [score, setScore] = useState(0)
  const started = useRef(false)

  const signals = useMemo(() => PRIMARY_EXAMPLE.result?.signals ?? [], [])
  const target = PRIMARY_EXAMPLE.score ?? 68
  const scored = shown >= signals.length

  useEffect(() => {
    const node = ref.current
    if (!node || started.current) return

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      started.current = true
      const skip = window.setTimeout(() => {
        setShown(signals.length)
        setScore(target)
      }, 0)
      return () => window.clearTimeout(skip)
    }

    const io = new IntersectionObserver(
      (entries) => {
        if (!entries[0]?.isIntersecting || started.current) return
        started.current = true
        io.disconnect()
        signals.forEach((_, i) => window.setTimeout(() => setShown(i + 1), 160 + i * 105))
      },
      { threshold: 0.3 },
    )
    io.observe(node)
    return () => io.disconnect()
  }, [signals, target])

  useEffect(() => {
    if (!scored || score >= target) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      const skip = window.setTimeout(() => setScore(target), 0)
      return () => window.clearTimeout(skip)
    }
    const tick = window.setInterval(() => setScore((c) => Math.min(c + 4, target)), 18)
    return () => window.clearInterval(tick)
  }, [scored, score, target])

  return (
    <section
      ref={ref}
      className="stage stage-lit scene-in scene-out relative overflow-hidden py-24 sm:py-32"
    >
      <div className="relative mx-auto max-w-6xl px-5 sm:px-6">
        <p className="label text-electric text-center">04 · The verdict</p>

        <div className="mt-14 grid grid-cols-2 items-center gap-x-6 gap-y-7 sm:gap-x-10 lg:mt-16 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)_minmax(0,1fr)] lg:gap-x-14 lg:gap-y-9">
          {signals.map((s, i) => (
            <div
              key={s.kind}
              style={
                {
                  '--from-x': FROM[i]?.split(',')[0],
                  '--from-y': FROM[i]?.split(',')[1],
                } as React.CSSProperties
              }
              className={cn(
                'border-t border-white/12 pt-3.5',
                PLACE[i],
                i < shown ? 'motion-safe:anim-converge' : 'invisible',
              )}
            >
              <p className="label text-white/40">{s.label}</p>
              <p className={cn('mt-2 text-[0.9375rem] leading-snug', TONE[s.tone])}>{s.detail}</p>
            </div>
          ))}

          {/* The score sits in the middle of its own evidence. */}
          <div className="col-span-2 py-4 text-center lg:col-span-1 lg:col-start-2 lg:row-span-3 lg:row-start-1 lg:py-0">
            {/* `/100` carries its own size: an em-relative size here resolves
                against the paragraph, not against the score beside it. */}
            {/* A dash, not a zero, until the evidence is in: a display-size 0
                sitting there for a second reads as a score of nothing rather
                than as a number that has not been reached yet. */}
            <p className="tnum flex items-start justify-center text-white">
              <span className={cn('text-display font-semibold', !scored && 'text-white/20')}>
                {scored ? score : '—'}
              </span>
              <span className="mt-3 ml-1.5 text-[1rem] text-white/35 sm:mt-6 sm:text-[1.375rem]">
                /100
              </span>
            </p>

            <p
              className={cn(
                'text-think-lift text-statement mt-2 font-serif font-medium',
                scored ? 'motion-safe:anim-wipe' : 'invisible',
              )}
            >
              Think twice
            </p>

            <p
              className={cn(
                'text-lead mx-auto mt-6 max-w-[26ch] text-white/60',
                scored ? 'motion-safe:anim-land' : 'invisible',
              )}
            >
              {PRIMARY_EXAMPLE.summary}
            </p>
          </div>
        </div>

        <Disclosure tone="dark" className="mt-16 text-center">
          Illustrative analysis — not a real evaluation of a real seller.
        </Disclosure>
      </div>
    </section>
  )
}
