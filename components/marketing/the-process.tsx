'use client'

import { useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils/cn'

/**
 * Scene 03 — the process.
 *
 * One panel, pinned, that transforms three times as the visitor scrolls past
 * it: a link goes in, Worth reads it, a verdict comes out. The scroll is the
 * transport — you are moving the process forward yourself, which is a better
 * demonstration of "paste it and Worth does the rest" than three cards
 * describing the same thing would be.
 *
 * The pin is `position: sticky` on a tall track, so there is no scroll
 * hijacking: the page never stops responding to a flick, and the panel simply
 * holds still while its own contents change.
 *
 * Only the *stage index* goes through React — one integer, changed twice over
 * the whole section. The panel's own contents cross-fade in CSS.
 *
 * Under prefers-reduced-motion the track collapses and all three states render
 * one after another, so nothing is hidden behind a scroll the visitor may not
 * be able to perform comfortably.
 */

const STAGES = [
  {
    key: 'input',
    label: 'You paste',
    caption: 'A checkout, a product page, a subscription, a course. Anything with a price on it.',
  },
  {
    key: 'analyse',
    label: 'Worth reads',
    caption:
      'Price and fees, what buyers actually report, who is selling it, what happens if you want out, and what else is out there.',
  },
  {
    key: 'verdict',
    label: 'You decide',
    caption: 'One number, one call, and the difference between the two prices.',
  },
] as const

export function TheProcess() {
  const trackRef = useRef<HTMLDivElement>(null)
  const [stage, setStage] = useState(0)
  const [flat, setFlat] = useState(false)

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      const skip = window.setTimeout(() => setFlat(true), 0)
      return () => window.clearTimeout(skip)
    }

    const node = trackRef.current
    if (!node) return

    let frame = 0
    const read = () => {
      frame = 0
      const box = node.getBoundingClientRect()
      const span = box.height - window.innerHeight
      if (span <= 0) return
      const p = Math.min(1, Math.max(0, -box.top / span))
      setStage(p < 0.34 ? 0 : p < 0.68 ? 1 : 2)
    }
    const onScroll = () => {
      if (frame) return
      frame = requestAnimationFrame(read)
    }

    read()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      if (frame) cancelAnimationFrame(frame)
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
  }, [])

  if (flat) return <FlatProcess />

  return (
    <section id="how-it-works" className="stage stage-lit scene-in scene-out relative scroll-mt-0">
      {/* The track. Three viewports tall; the panel is pinned inside it. */}
      <div ref={trackRef} className="relative h-[300vh]">
        <div className="sticky top-0 flex h-screen flex-col justify-center overflow-hidden">
          <div className="mx-auto w-full max-w-6xl px-5 sm:px-6">
            <p className="label text-electric">03 · How it works</p>

            <div className="mt-8 grid grid-cols-1 items-center gap-10 lg:mt-10 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1fr)] lg:gap-16">
              {/* The narration. The current step is the only lit one. */}
              <ol className="flex flex-col gap-2">
                {STAGES.map((s, i) => (
                  <li
                    key={s.key}
                    className={cn(
                      'border-l py-4 pl-5 transition-colors duration-500 motion-reduce:transition-none',
                      i === stage ? 'border-electric' : 'border-white/10',
                    )}
                  >
                    <p
                      className={cn(
                        'font-serif text-[1.75rem] leading-none font-medium tracking-[-0.02em] transition-colors duration-500 sm:text-[2.25rem]',
                        'motion-reduce:transition-none',
                        i === stage ? 'text-white' : 'text-white/25',
                      )}
                    >
                      {s.label}
                    </p>
                    <p
                      className={cn(
                        'mt-2 max-w-[42ch] text-[0.9375rem] leading-snug transition-all duration-500',
                        'motion-reduce:transition-none',
                        i === stage
                          ? 'max-h-24 text-white/55 opacity-100'
                          : 'max-h-0 overflow-hidden opacity-0',
                      )}
                    >
                      {s.caption}
                    </p>
                  </li>
                ))}
              </ol>

              {/* The panel. Same object throughout; only its contents change. */}
              {/* The halo lives on a wrapper: on the panel itself it would sit
                  behind the panel's own opaque fill and never be seen. */}
              <div className="halo relative">
                <div className="glass glass-rim rounded-stage relative min-h-[19rem] overflow-hidden sm:min-h-[21rem]">
                  <PanelInput active={stage === 0} />
                  <PanelAnalyse active={stage === 1} />
                  <PanelVerdict active={stage === 2} />
                </div>
              </div>
            </div>

            <p className="mt-8 text-[0.75rem] text-white/25">
              Illustrative analysis — not a real evaluation of a real seller.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}

/** Cross-fade wrapper: all three states are mounted, one is shown. */
function Panel({ active, children }: { active: boolean; children: React.ReactNode }) {
  return (
    <div
      aria-hidden={!active}
      className={cn(
        'absolute inset-0 flex flex-col justify-center p-6 transition-all duration-500 sm:p-8',
        'motion-reduce:transition-none',
        active ? 'translate-y-0 opacity-100' : 'pointer-events-none translate-y-2 opacity-0',
      )}
    >
      {children}
    </div>
  )
}

function PanelInput({ active }: { active: boolean }) {
  return (
    <Panel active={active}>
      <p className="label text-white/35">Paste anything with a price on it</p>
      <div className="mt-5 flex items-center gap-3 rounded-full border border-white/12 bg-white/[0.04] px-4 py-3.5">
        <span className="min-w-0 flex-1 truncate font-mono text-[0.8125rem] text-white/70">
          example.com/checkout
        </span>
        <span className="bg-violet shrink-0 rounded-full px-3.5 py-1.5 text-[0.75rem] font-semibold text-white">
          Analyze
        </span>
      </div>
      <div className="mt-6 flex flex-wrap gap-2">
        {['Checkout', 'Subscription', 'Course', 'Product page'].map((k) => (
          <span
            key={k}
            className="rounded-full border border-white/10 px-3 py-1.5 text-[0.75rem] text-white/45"
          >
            {k}
          </span>
        ))}
      </div>
    </Panel>
  )
}

function PanelAnalyse({ active }: { active: boolean }) {
  const rows = [
    ['Price', '€892 advertised', 'bg-think-lift'],
    ['Fees', '€115 at checkout', 'bg-skip-lift'],
    ['Reviews', '4.5 · 1,284', 'bg-buy-lift'],
    ['Trust', 'Established seller', 'bg-buy-lift'],
    ['Risk', 'Locked in at 14 days', 'bg-skip-lift'],
    ['Alternatives', '€724 elsewhere', 'bg-buy-lift'],
  ] as const

  return (
    <Panel active={active}>
      <p className="label text-electric">Reading six things</p>
      <ul className="mt-5 flex flex-col gap-3">
        {rows.map(([k, v, dot], i) => (
          <li
            key={k}
            className={cn(
              'flex items-baseline gap-3 transition-all duration-500 motion-reduce:transition-none',
              active ? 'translate-x-0 opacity-100' : '-translate-x-1 opacity-0',
            )}
            style={{ transitionDelay: active ? `${i * 70}ms` : '0ms' }}
          >
            <span aria-hidden className={cn('size-1.5 shrink-0 rounded-full', dot)} />
            <span className="label w-[6.75rem] shrink-0 text-white/35">{k}</span>
            <span className="text-[0.875rem] text-white/70">{v}</span>
          </li>
        ))}
      </ul>
    </Panel>
  )
}

function PanelVerdict({ active }: { active: boolean }) {
  return (
    <Panel active={active}>
      <p className="label text-white/35">Worth verdict</p>
      <p className="tnum mt-4 flex items-start text-white">
        <span className="text-[4.5rem] leading-none font-semibold tracking-[-0.05em] sm:text-[5.5rem]">
          68
        </span>
        <span className="mt-3 ml-1.5 text-[0.9375rem] text-white/35">/100</span>
      </p>
      <p className="text-think-lift mt-2 font-serif text-[1.75rem] leading-none font-medium tracking-[-0.02em] sm:text-[2rem]">
        Think twice
      </p>
      <div className="mt-6 flex items-center gap-3 border-t border-white/10 pt-5">
        <span className="tnum text-[1rem] text-white/25 line-through">€1,007</span>
        <span aria-hidden className="text-electric">
          →
        </span>
        <span className="tnum text-[1.5rem] leading-none font-semibold tracking-[-0.03em] text-white">
          €724
        </span>
        <span className="bg-buy/20 text-buy-lift ml-auto rounded-full px-2.5 py-1 text-[0.75rem] font-medium">
          −€283
        </span>
      </div>
    </Panel>
  )
}

/**
 * The reduced-motion version. No pin and no transforms — the same three states
 * as three stacked panels, in order.
 */
function FlatProcess() {
  return (
    <section
      id="how-it-works"
      className="stage stage-lit scene-in scene-out relative overflow-hidden py-24 sm:py-32"
    >
      <div className="mx-auto w-full max-w-3xl px-5 sm:px-6">
        <p className="label text-electric">03 · How it works</p>
        <div className="mt-10 flex flex-col gap-10">
          {STAGES.map((s, i) => (
            <div key={s.key} className="border-l border-white/12 pl-5">
              <p className="font-serif text-[1.75rem] leading-none font-medium text-white">
                {s.label}
              </p>
              <p className="mt-2 max-w-[46ch] text-[0.9375rem] text-white/55">{s.caption}</p>
              <div className="glass rounded-object relative mt-6 min-h-[17rem] overflow-hidden">
                {i === 0 && <PanelInput active />}
                {i === 1 && <PanelAnalyse active />}
                {i === 2 && <PanelVerdict active />}
              </div>
            </div>
          ))}
        </div>
        <p className="mt-8 text-[0.75rem] text-white/25">
          Illustrative analysis — not a real evaluation of a real seller.
        </p>
      </div>
    </section>
  )
}
