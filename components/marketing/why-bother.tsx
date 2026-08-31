'use client'

import { useEffect, useRef, useState } from 'react'
import { Disclosure, Section, Eyebrow, Statement } from './section'
import { COMPARISON_EXAMPLE, MONEY_EXAMPLE, RESEARCH_FRAGMENTS } from '@/lib/analysis/fixtures'
import { cn } from '@/lib/utils/cn'

/**
 * Beat 02 — why bother.
 *
 * Three chapters, and deliberately three *different* pieces of design. A
 * three-up grid of identical cards would have been quicker and would have said
 * that these are three interchangeable features; they are not. They are the
 * three things a person actually does badly on their own, in order:
 *
 *   01  RESEARCH CHAOS → ORDER   scattered fragments reorganising into a list
 *   02  THE REAL PRICE           money, at the largest type on the page
 *   03  THE BETTER OPTION        a comparison the alternative walks into
 *
 * Each chapter animates once, when it is first scrolled into view, and only
 * the thing that is being demonstrated moves. Under prefers-reduced-motion the
 * finished state is what renders.
 */

/** Runs a callback once, the first time the element is on screen. */
function useOnceInView<T extends HTMLElement>(onEnter: () => void, threshold = 0.4) {
  const ref = useRef<T>(null)
  const done = useRef(false)
  useEffect(() => {
    const node = ref.current
    if (!node || done.current) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      done.current = true
      onEnter()
      return
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (!entries[0]?.isIntersecting || done.current) return
        done.current = true
        io.disconnect()
        onEnter()
      },
      { threshold },
    )
    io.observe(node)
    return () => io.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  return ref
}

export function WhyBother() {
  return (
    <>
      <ResearchChaos />
      <RealPrice />
      <BetterOption />
    </>
  )
}

/* ==========================================================================
   01 — Research chaos becomes one answer.
   The fragments are placed as a scattered field, then reorganise into a single
   ordered column. The movement is the argument, so nothing else moves.
   ========================================================================== */

/**
 * How far each fragment is displaced from its place in the finished list.
 *
 * The ordered list is the real layout: ten rows in normal flow. Scatter is
 * expressed as a transform *off* those rows, so the animation is pure
 * translate/scale — nothing animates `left`, `top` or `width`, which are not
 * compositor properties and which made this section stagger visibly mid-flight.
 *
 * `indent` is a percentage of the row's own (full) width and never exceeds 44,
 * while a scattered fragment is capped at 52% wide — so the widest fragment in
 * the furthest position still lands inside the field.
 */
const SCATTER = [
  { indent: 2, rows: -0.4, s: 1 },
  { indent: 40, rows: -1.1, s: 0.86 },
  { indent: 18, rows: 0.7, s: 0.94 },
  { indent: 44, rows: 0.2, s: 1 },
  { indent: 0, rows: 1.4, s: 0.82 },
  { indent: 26, rows: -0.6, s: 0.9 },
  { indent: 42, rows: 0.9, s: 0.86 },
  { indent: 6, rows: -1.3, s: 0.96 },
  { indent: 30, rows: 1.1, s: 0.84 },
  { indent: 14, rows: -0.8, s: 0.9 },
]

/** One row of the finished list, in rem. Also the unit scatter is measured in. */
const ROW = 2.6

function ResearchChaos() {
  const [ordered, setOrdered] = useState(false)
  const ref = useOnceInView<HTMLElement>(() => {
    window.setTimeout(() => setOrdered(true), 800)
  }, 0.25)

  return (
    <section ref={ref} className="scene scene-in scene-out relative overflow-hidden py-20 sm:py-28">
      <div className="relative mx-auto max-w-5xl px-5 sm:px-6">
        <p className="label text-violet-lift">02 · The research</p>
        <p className="text-statement mt-5 max-w-[16ch] font-serif font-medium text-white">
          Stop opening fifteen tabs.
        </p>
        <p className="text-lead mt-6 max-w-[42ch] text-white/55">
          The price, the fees, the reviews, the terms, and whatever else is out there at a better
          price. Worth reads all of it in one pass.
        </p>

        {/* The field. Ten fragments, displaced, then settling into one list. */}
        <ul className="mt-12 flex flex-col sm:mt-16">
          {RESEARCH_FRAGMENTS.map((f, i) => {
            const pos = SCATTER[i] ?? SCATTER[0]!
            return (
              <li
                key={f.text}
                style={{
                  height: `${ROW}rem`,
                  transform: ordered
                    ? 'none'
                    : `translate3d(${pos.indent}%, ${pos.rows * ROW}rem, 0) scale(${pos.s})`,
                  transformOrigin: 'left center',
                }}
                className={cn(
                  'transition-[transform,opacity] duration-[900ms] ease-[cubic-bezier(0.22,1,0.36,1)]',
                  'motion-reduce:transition-none',
                  ordered ? 'opacity-100' : 'opacity-65',
                )}
              >
                <div
                  className={cn(
                    'flex items-baseline gap-3 transition-colors duration-700',
                    'motion-reduce:transition-none',
                    ordered ? 'border-b border-white/10 pb-2.5' : 'max-w-[52%]',
                  )}
                >
                  <span
                    className={cn(
                      'text-[0.9375rem] font-medium sm:text-[1.0625rem]',
                      ordered ? 'text-white' : 'text-white/70',
                    )}
                  >
                    {f.text}
                  </span>
                  <span className="truncate text-[0.6875rem] text-white/35">{f.sub}</span>
                  <span
                    aria-hidden
                    className={cn(
                      'text-buy-lift ml-auto text-[0.6875rem] transition-opacity duration-500',
                      'motion-reduce:transition-none',
                      ordered ? 'opacity-100' : 'opacity-0',
                    )}
                  >
                    read
                  </span>
                </div>
              </li>
            )
          })}
        </ul>

        <p
          className={cn(
            'text-lead mt-8 max-w-[38ch] transition-opacity duration-700 motion-reduce:transition-none',
            ordered ? 'text-white/70 opacity-100' : 'opacity-0',
          )}
        >
          Ten things you would have had to find yourself. One pass, one answer.
        </p>

        <Disclosure tone="dark" className="mt-8">
          Illustrative fragments — not real listings, reviews or prices.
        </Disclosure>
      </div>
    </section>
  )
}

/* ==========================================================================
   02 — The real price.
   Money, at the largest type on the page. The advertised figure lands first,
   the additions reveal, the true total resolves, and only then does the
   alternative arrive. Type and space do the work; there is no card.
   ========================================================================== */

function RealPrice() {
  const [phase, setPhase] = useState(0)
  const ref = useOnceInView<HTMLElement>(() => {
    ;[300, 620, 1000, 1400].forEach((at, i) =>
      window.setTimeout(() => setPhase(i + 1), at),
    )
  }, 0.18)

  return (
    <section ref={ref}>
      <Section width="wide">
        <div className="max-w-[34rem]">
          <Eyebrow index="03">The real price</Eyebrow>
          <Statement className="mt-5 max-w-[18ch]">
            Know what you’re actually paying for.
          </Statement>
        </div>

        <div className="mt-12 sm:mt-16">
          {/* Advertised. */}
          <p className="label text-faint">{MONEY_EXAMPLE.base.label}</p>
          <p className="tnum text-display text-ink mt-3 font-semibold">
            {MONEY_EXAMPLE.base.amount}
          </p>

          {/* What gets added. */}
          <ul className="mt-8 flex flex-col gap-3">
            {MONEY_EXAMPLE.additions.map((a, i) => (
              <li
                key={a.label}
                className={cn(
                  'border-line flex items-baseline gap-4 border-t pt-3 transition-all duration-500',
                  'motion-reduce:transition-none',
                  phase >= 1 + i ? 'translate-y-0 opacity-100' : 'translate-y-2 opacity-0',
                )}
              >
                <span className="tnum text-skip text-figure-sm font-semibold">+ {a.amount}</span>
                <span className="text-graphite text-[0.9375rem]">{a.label}</span>
              </li>
            ))}
          </ul>

          {/* The true total. */}
          <div
            className={cn(
              'border-ink mt-8 border-t-2 pt-7 transition-all duration-700',
              'motion-reduce:transition-none',
              phase >= 3 ? 'translate-y-0 opacity-100' : 'translate-y-3 opacity-0',
            )}
          >
            <p className="label text-ink">{MONEY_EXAMPLE.actual.label}</p>
            <p className="tnum text-display text-ink mt-3 font-semibold">
              {MONEY_EXAMPLE.actual.amount}
            </p>
          </div>

          {/* And what Worth found instead. */}
          <div
            className={cn(
              'border-violet mt-10 border-t-2 pt-7 transition-all duration-700',
              'motion-reduce:transition-none',
              phase >= 4 ? 'translate-y-0 opacity-100' : 'translate-y-3 opacity-0',
            )}
          >
            <p className="label text-violet">{MONEY_EXAMPLE.better.label}</p>
            <div className="mt-3 flex flex-wrap items-baseline gap-x-6 gap-y-2">
              <p className="tnum text-display text-ink font-semibold">
                {MONEY_EXAMPLE.better.amount}
              </p>
              <p className="tnum text-buy text-figure-sm font-semibold">
                −{MONEY_EXAMPLE.saving}
              </p>
            </div>
          </div>
        </div>

        <p className="text-lead text-graphite mt-16 max-w-[46ch]">
          Worth pays for itself the first time it catches one of these. That’s the pitch — not
          saved time, not smarter shopping. Money you were about to hand over and didn’t need to.
        </p>

        <Disclosure className="mt-6">
          An illustrative example. Worth has no real users yet and makes no claim about savings.
        </Disclosure>
      </Section>
    </section>
  )
}

/* ==========================================================================
   03 — The better option.
   A comparison the alternative walks into: the option you found is already
   there, and Worth's arrives from the side and settles beside it. The delta is
   the punchline, so it lands last.
   ========================================================================== */

function BetterOption() {
  const [arrived, setArrived] = useState(false)
  const [delta, setDelta] = useState(false)
  const ref = useOnceInView<HTMLElement>(() => {
    window.setTimeout(() => setArrived(true), 350)
    window.setTimeout(() => setDelta(true), 1150)
  }, 0.35)

  return (
    <section ref={ref} className="scene scene-in scene-out relative overflow-hidden py-20 sm:py-28">
      <div className="relative mx-auto max-w-5xl px-5 sm:px-6">
        <p className="label text-violet-lift">04 · The alternative</p>
        <p className="text-statement mt-5 max-w-[16ch] font-serif font-medium text-white">
          Find the better option.
        </p>
        <p className="text-lead mt-6 max-w-[42ch] text-white/55">
          Worth doesn’t only judge the thing in front of you. It goes looking for the same thing
          cheaper, and the better thing at the same price.
        </p>

        <div className="mt-12 grid grid-cols-1 gap-6 sm:mt-16 sm:grid-cols-2 sm:gap-8">
          <Side data={COMPARISON_EXAMPLE.found} tone="found" />
          {/* Wiped in with clip-path rather than translated in: a horizontal
              transform on a full-width column pushes content past the section
              edge for the length of the animation, which is a real overflow
              even when a parent clips it. The wipe reads as arrival and never
              leaves the box. */}
          <div
            className={cn(
              'transition-[clip-path,opacity] duration-[850ms] ease-[cubic-bezier(0.22,1,0.36,1)]',
              'motion-reduce:transition-none',
              arrived ? 'opacity-100' : 'opacity-0',
            )}
            style={{ clipPath: arrived ? 'inset(0 0 0 0)' : 'inset(0 100% 0 0)' }}
          >
            <Side data={COMPARISON_EXAMPLE.worth} tone="worth" />
          </div>
        </div>

        <p
          className={cn(
            'mt-10 transition-all duration-700 motion-reduce:transition-none',
            delta ? 'translate-y-0 opacity-100' : 'translate-y-2 opacity-0',
          )}
        >
          <span className="tnum text-buy-lift text-figure font-semibold">
            −{COMPARISON_EXAMPLE.saving}
          </span>
          <span className="text-lead mt-2 block max-w-[34ch] text-white/60">
            Same capability, better terms, and you can leave whenever you want.
          </span>
        </p>

        <Disclosure tone="dark" className="mt-8">
          Illustrative comparison — not real offers, prices or ratings.
        </Disclosure>
      </div>
    </section>
  )
}

function Side({
  data,
  tone,
}: {
  data: { heading: string; price: string; rows: readonly (readonly [string, string])[] }
  tone: 'found' | 'worth'
}) {
  const worth = tone === 'worth'
  return (
    <div className={cn('border-t-2 pt-6', worth ? 'border-violet' : 'border-white/20')}>
      <p className={cn('label', worth ? 'text-violet-lift' : 'text-white/40')}>{data.heading}</p>
      <p
        className={cn(
          'tnum text-figure mt-4 font-semibold',
          worth ? 'text-white' : 'text-white/45',
        )}
      >
        {data.price}
      </p>
      <dl className="mt-7 flex flex-col gap-3">
        {data.rows.map(([k, v]) => (
          <div key={k} className="flex items-baseline justify-between gap-4 border-t border-white/8 pt-3">
            <dt className="text-[0.8125rem] text-white/40">{k}</dt>
            <dd className={cn('text-[0.9375rem]', worth ? 'text-white' : 'text-white/55')}>{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
