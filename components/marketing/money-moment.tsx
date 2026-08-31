'use client'

import { useEffect, useRef, useState } from 'react'
import { Section, Eyebrow, Statement, Disclosure } from './section'

/**
 * Beat 06 — the money.
 *
 * The price counts down from €399 to €329 and the saving resolves underneath,
 * because that transition is literally what the product does for you. It's the
 * one number on the page worth animating, it runs once when the section is on
 * screen, and the vertical layout means it reads identically on a phone.
 */
export function MoneyMoment() {
  const ref = useRef<HTMLDivElement>(null)
  const [price, setPrice] = useState(399)
  const [done, setDone] = useState(false)
  const hasRun = useRef(false)

  useEffect(() => {
    const node = ref.current
    if (!node) return

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      const skip = window.setTimeout(() => {
        setPrice(329)
        setDone(true)
      }, 0)
      return () => window.clearTimeout(skip)
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries[0]?.isIntersecting || hasRun.current) return
        hasRun.current = true
        observer.disconnect()

        const start = performance.now()
        const tick = (now: number) => {
          const t = Math.min((now - start) / 950, 1)
          const eased = 1 - Math.pow(1 - t, 3)
          setPrice(Math.round(399 - eased * 70))
          if (t < 1) requestAnimationFrame(tick)
          else setDone(true)
        }
        requestAnimationFrame(tick)
      },
      { threshold: 0.35 },
    )

    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  return (
    <Section>
      <div className="max-w-[34rem]">
        <Eyebrow index="06">You keep the difference</Eyebrow>
        <Statement className="mt-5 max-w-[16ch]">Same thing. €70 less.</Statement>
      </div>

      <div ref={ref} className="mt-16 sm:mt-24">
        {/* One column, centred, at the largest scale the page uses for money.
            The drop reads as a drop on any width, and the saving lands last and
            biggest because it is the only number that is the visitor's. */}
        <div className="flex flex-col items-center gap-5 text-center">
          <Row label="You were about to spend" value="€399" muted />
          <Connector />
          <Row label="Worth found" value={`€${price}`} accent />
          <Connector />
          <Row label="You keep" value="€70" saving huge faded={!done} />
        </div>

        <p className="text-lead text-graphite mx-auto mt-16 max-w-[46ch] text-center">
          Worth pays for itself the first time it catches one of these. That’s the pitch — not saved
          time, not smarter shopping. Money you were about to hand over and didn’t need to.
        </p>

        <Disclosure className="mx-auto mt-6 text-center">
          An illustrative example. Worth has no real users yet and makes no claim about savings.
        </Disclosure>
      </div>
    </Section>
  )
}

function Row({
  label,
  value,
  muted,
  accent,
  saving,
  huge,
  faded,
}: {
  label: string
  value: string
  muted?: boolean
  accent?: boolean
  saving?: boolean
  huge?: boolean
  faded?: boolean
}) {
  return (
    <div
      className={`flex flex-col items-center gap-2 transition-opacity duration-500 motion-reduce:transition-none ${
        faded ? 'opacity-0' : 'opacity-100'
      }`}
    >
      <span className="label text-faint">{label}</span>
      <span
        className={`tnum font-semibold tracking-[-0.045em] ${huge ? 'text-display' : 'text-figure'} ${
          saving ? 'text-buy' : muted ? 'text-faint line-through decoration-1' : 'text-ink'
        } ${accent ? 'text-ink' : ''}`}
      >
        {value}
      </span>
    </div>
  )
}

/** The drop, drawn. */
function Connector() {
  return (
    <div className="flex justify-center" aria-hidden>
      <svg width="14" height="34" viewBox="0 0 14 34" fill="none">
        <path
          d="M7 0v29M1.5 23.5 7 29.5l5.5-6"
          stroke="var(--color-violet)"
          strokeWidth="1.8"
          strokeLinecap="square"
        />
      </svg>
    </div>
  )
}
