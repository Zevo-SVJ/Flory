'use client'

import { useScrollProgress } from '@/lib/hooks/use-scroll-progress'
import { cn } from '@/lib/utils/cn'

/**
 * Scene 02 — the question.
 *
 * The visitor's own question, at the size it deserves, standing in the middle
 * of the contradictory signals they would otherwise have to reconcile
 * themselves. As the scene scrolls past, those signals converge on it: they
 * start scattered across the field and end stacked behind the question, which
 * is exactly what Worth does to them.
 *
 * The convergence is driven by scroll rather than by a timer, so the visitor
 * is the one collapsing the noise. Nothing here reads layout while it moves:
 * `--p` becomes a `translate` and an `opacity`, and that is all.
 *
 * These are illustrative fragments — the kinds of thing a person finds, not
 * real reviews, prices or terms.
 */

interface Signal {
  text: string
  sub: string
  /** Where it starts, as a percentage of the field, and how far back it sits. */
  x: number
  y: number
  depth: number
}

const SIGNALS: Signal[] = [
  { text: '4.5 ★', sub: '1,284 reviews', x: 8, y: 6, depth: 1 },
  { text: '“Support is great”', sub: 'review, 2025', x: 68, y: 2, depth: 0.7 },
  { text: '€892', sub: 'advertised', x: 2, y: 34, depth: 0.85 },
  { text: '“Hidden fees”', sub: 'review, 2025', x: 74, y: 30, depth: 1 },
  { text: 'Annual only', sub: 'billing terms', x: 12, y: 62, depth: 0.6 },
  { text: '€724', sub: 'another provider', x: 70, y: 60, depth: 0.9 },
  { text: '14 days', sub: 'refund window', x: 30, y: 82, depth: 0.75 },
  { text: '4.7 ★', sub: 'competitor', x: 62, y: 86, depth: 0.65 },
]

export function TheQuestion() {
  const ref = useScrollProgress<HTMLElement>({ pad: 0.15 })

  return (
    <section
      ref={ref}
      className="stage stage-lit scene-in scene-out depth relative overflow-hidden py-24 sm:py-32"
    >
      <div className="relative z-[1] mx-auto max-w-5xl px-5 sm:px-6">
        {/* The field. The question sits inside it, not above it. */}
        <div className="relative min-h-[30rem] sm:min-h-[34rem]">
          {SIGNALS.map((s) => (
            <span
              key={s.text}
              aria-hidden
              style={
                {
                  left: `${s.x}%`,
                  top: `${s.y}%`,
                  /* Converge toward the centre of the field, and dim as they
                     go: the closer they get to the question, the less each one
                     matters on its own. */
                  '--dx': `${(50 - s.x) * 0.9}%`,
                  '--dy': `${(50 - s.y) * 0.55}%`,
                  '--o': s.depth,
                } as React.CSSProperties
              }
              className={cn(
                'absolute max-w-[42%] origin-left',
                'translate-x-[calc(var(--dx)*var(--p,0))] translate-y-[calc(var(--dy)*var(--p,0))]',
                'opacity-[calc(var(--o)*(1-var(--p,0)*0.72))]',
                'motion-reduce:translate-x-0 motion-reduce:translate-y-0 motion-reduce:opacity-100',
              )}
            >
              <span
                className="block text-[0.9375rem] leading-tight font-medium whitespace-nowrap text-white/70 sm:text-[1.0625rem]"
                style={{ fontSize: `calc(0.9375rem + ${s.depth} * 0.2rem)` }}
              >
                {s.text}
              </span>
              <span className="block text-[0.6875rem] text-white/30">{s.sub}</span>
            </span>
          ))}

          {/* The question itself, lit from behind. */}
          <div className="halo absolute inset-x-[10%] top-1/2 -translate-y-1/2 text-center">
            <p className="text-statement mx-auto max-w-[13ch] font-serif font-medium text-balance text-white">
              Should I <span className="text-electric">actually</span> buy this?
            </p>
          </div>
        </div>

        <p className="text-lead mx-auto mt-4 max-w-[40ch] text-center text-white/55">
          Eight half-answers that don’t agree with each other. Worth reads all of them and returns
          one.
        </p>

        <p className="mt-10 text-center text-[0.75rem] text-white/25">
          Illustrative fragments — not real reviews, prices or terms.
        </p>
      </div>
    </section>
  )
}
