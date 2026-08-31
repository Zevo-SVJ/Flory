'use client'

import { AnalyzeInput } from '@/components/worth/analyze-input'
import { useScrollProgress } from '@/lib/hooks/use-scroll-progress'

/**
 * Scene 07 — the close.
 *
 * The brightest screen on the page, and the last one. Everything before it was
 * Worth explaining itself; this is Worth waiting. So there is one line, one
 * field, and a single source of light rising behind them — no second button,
 * no newsletter, nothing else competing for the click.
 *
 * The light and the rings drift apart as the scene arrives, which is the only
 * continuous motion on the page. It is slow enough to read as the room
 * breathing rather than as an animation playing.
 */
export function FinalCta() {
  const ref = useScrollProgress<HTMLElement>({ pad: 0.2 })

  return (
    <section
      ref={ref}
      className="stage stage-grid scene-in depth relative overflow-hidden py-28 sm:py-36"
    >
      {/* The source. A pool of Worth Violet rising from the bottom edge, which
          is why this screen reads as an ending rather than another section.
          It has to sit *inside* the section: pushed below it, the section's own
          overflow clip removes exactly the part that was meant to be seen. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 bottom-0 h-[78%] bg-[radial-gradient(64%_92%_at_50%_106%,rgba(139,92,255,0.5)_0%,rgba(69,38,214,0.3)_34%,rgba(42,31,143,0.14)_58%,transparent_78%)]"
      />

      {/* Rings, spreading outward from the source. Scale only — no layout. */}
      <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="absolute bottom-0 left-1/2 aspect-square w-[130%] max-w-[70rem] -translate-x-1/2 translate-y-[42%] rounded-full border border-white/[0.11]"
            style={{
              transform: `translate(-50%, 50%) scale(calc(${0.52 + i * 0.24} + var(--p, 0.5) * 0.1))`,
            }}
          />
        ))}
      </div>

      <div className="relative z-[1] mx-auto max-w-6xl px-5 sm:px-6">
        <div className="mx-auto flex max-w-[40rem] flex-col items-center text-center">
          <h2 className="text-statement max-w-[14ch] font-serif font-medium text-balance text-white">
            Before you spend it, <span className="text-electric">check it</span>.
          </h2>

          <p className="text-lead mt-6 text-white/55">Paste the link. Get the verdict.</p>

          <div className="mt-11 w-full">
            <AnalyzeInput tone="dark" />
          </div>
        </div>
      </div>
    </section>
  )
}
