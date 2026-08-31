'use client'

import { useEffect, useRef, useState } from 'react'
import { Section, Beat } from './section'

/**
 * The money.
 *
 * The price is animated *down* — the figure counts from €399 to €329 and the
 * saving resolves underneath — because that transition is literally what the
 * product does for you. It's the one number on the page worth animating, and
 * it only runs once, when the section is actually on screen.
 *
 * Under prefers-reduced-motion the final figures render immediately.
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
          const t = Math.min((now - start) / 900, 1)
          const eased = 1 - Math.pow(1 - t, 3)
          setPrice(Math.round(399 - eased * 70))
          if (t < 1) requestAnimationFrame(tick)
          else setDone(true)
        }
        requestAnimationFrame(tick)
      },
      { threshold: 0.4 },
    )

    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  return (
    <Section>
      <div className="flex flex-col gap-3">
        <Beat index="05">You keep the difference</Beat>
        <h2 className="text-statement text-ink max-w-[22ch] font-serif font-medium">
          Same headphones. Same warranty. Seventy euro.
        </h2>
      </div>

      <div ref={ref} className="mt-12 sm:mt-16">
        <div className="grid grid-cols-1 items-end gap-8 sm:grid-cols-[auto_auto_1fr] sm:gap-10">
          <div>
            <span className="label text-graphite">Listed price</span>
            <p className="tnum text-figure text-faint mt-2 font-medium line-through decoration-1">
              €399
            </p>
          </div>

          <div>
            <span className="label text-worth">Worth found</span>
            <p className="tnum text-figure text-ink mt-2 font-semibold tracking-[-0.045em]">
              €{price}
            </p>
          </div>

          <div
            className={`transition-opacity duration-500 motion-reduce:transition-none ${
              done ? 'opacity-100' : 'opacity-0'
            }`}
          >
            <span className="label text-graphite">You save</span>
            <p className="tnum text-figure text-buy mt-2 font-semibold tracking-[-0.045em]">€70</p>
          </div>
        </div>

        <p className="text-lead text-graphite mt-8 max-w-[52ch]">
          Worth pays for itself the first time it catches one of these. That’s the whole pitch — not
          saved time, not smarter shopping. Money you were about to hand over and didn’t need to.
        </p>

        <p className="text-faint mt-5 text-[0.75rem]">
          An illustrative example. Worth has no real users yet and makes no claim about savings.
        </p>
      </div>
    </Section>
  )
}
