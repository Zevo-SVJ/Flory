'use client'

import { useEffect, useRef, useState } from 'react'
import type { Verdict } from '@/lib/analysis/types'
import { VERDICT_STYLE } from '@/lib/analysis/verdict'
import { cn } from '@/lib/utils/cn'

const STROKE: Record<Verdict, string> = {
  buy: 'var(--color-buy)',
  think_twice: 'var(--color-think)',
  skip: 'var(--color-skip)',
}

/**
 * The Worth Score.
 *
 * Counts up on entry because the number is the product's headline — the motion
 * makes it read as a conclusion being reached rather than a static figure.
 * Under prefers-reduced-motion it renders the final value immediately.
 */
export function ScoreDial({
  score,
  verdict,
  size = 'lg',
  className,
}: {
  score: number
  verdict: Verdict
  size?: 'sm' | 'lg'
  className?: string
}) {
  const [display, setDisplay] = useState(score)
  const ref = useRef<HTMLDivElement>(null)
  const hasRun = useRef(false)

  useEffect(() => {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduce || hasRun.current) return

    const node = ref.current
    if (!node) return

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0]
        if (!entry?.isIntersecting || hasRun.current) return
        hasRun.current = true
        observer.disconnect()

        const duration = 900
        const start = performance.now()
        setDisplay(0)

        const tick = (now: number) => {
          const t = Math.min((now - start) / duration, 1)
          // easeOutExpo — decisive, settles rather than drifts.
          const eased = t === 1 ? 1 : 1 - Math.pow(2, -10 * t)
          setDisplay(Math.round(eased * score))
          if (t < 1) requestAnimationFrame(tick)
        }
        requestAnimationFrame(tick)
      },
      { threshold: 0.5 },
    )

    observer.observe(node)
    return () => observer.disconnect()
  }, [score])

  const dimension = size === 'lg' ? 132 : 84
  const stroke = size === 'lg' ? 8 : 6
  const radius = (dimension - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const progress = circumference * (1 - display / 100)

  return (
    <div
      ref={ref}
      className={cn('relative shrink-0', className)}
      style={{ width: dimension, height: dimension }}
    >
      <svg
        width={dimension}
        height={dimension}
        viewBox={`0 0 ${dimension} ${dimension}`}
        aria-hidden
      >
        <circle
          cx={dimension / 2}
          cy={dimension / 2}
          r={radius}
          fill="none"
          stroke="var(--color-rule)"
          strokeWidth={stroke}
        />
        <circle
          cx={dimension / 2}
          cy={dimension / 2}
          r={radius}
          fill="none"
          stroke={STROKE[verdict]}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={progress}
          transform={`rotate(-90 ${dimension / 2} ${dimension / 2})`}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className={cn(
            'tnum leading-none font-semibold tracking-[-0.04em]',
            VERDICT_STYLE[verdict].text,
            size === 'lg' ? 'text-[2.75rem]' : 'text-[1.75rem]',
          )}
        >
          {display}
        </span>
        <span
          className={cn(
            'tnum text-faint mt-0.5 font-medium',
            size === 'lg' ? 'text-xs' : 'text-[0.625rem]',
          )}
        >
          / 100
        </span>
      </div>
      <span className="sr-only">Worth Score {score} out of 100</span>
    </div>
  )
}
