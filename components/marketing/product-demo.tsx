'use client'

import { useEffect, useState } from 'react'
import { Section, Eyebrow, Statement, Disclosure } from './section'
import { cn } from '@/lib/utils/cn'

/**
 * Beat 07 — Worth as a product you'd actually use.
 *
 * One phone, large, running the flow. This section used to be three phone
 * frames in a horizontal scroller: on a phone that meant two thirds of the
 * demonstration sat off-screen behind a swipe, and even on desktop it asked
 * the visitor to compare three small screens instead of watching one.
 *
 * A single device advancing through paste → checking → verdict shows the same
 * three states in the same space, in the order they actually happen, at a size
 * where the interface is readable. The stage tells you which step you are on.
 *
 * These are the real components' visual language, not a stock dashboard mock.
 */

const STEPS = [
  { label: 'Paste it', caption: 'Paste anything you’re about to buy.' },
  { label: 'Worth checks', caption: 'Price, reviews, seller, alternatives.' },
  { label: 'Verdict', caption: 'One number, one call, and the money.' },
] as const

export function ProductDemo() {
  const [step, setStep] = useState(0)

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      const skip = window.setTimeout(() => setStep(2), 0)
      return () => window.clearTimeout(skip)
    }
    const timers = [
      window.setTimeout(() => setStep(1), 2200),
      window.setTimeout(() => setStep(2), 4400),
    ]
    return () => timers.forEach(window.clearTimeout)
  }, [])

  return (
    <Section tone="sunk" width="wide">
      <div className="max-w-[34rem]">
        <Eyebrow index="07">Using it</Eyebrow>
        <Statement className="mt-5 max-w-[18ch]">Paste the link. Get the verdict.</Statement>
        <p className="text-lead text-graphite mt-6">
          No extension to install, no store to shop in, nothing to learn.
        </p>
      </div>

      <div className="mt-14 grid grid-cols-1 items-center gap-12 sm:mt-16 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)] lg:gap-20">
        {/* One device, large. */}
        <div className="mx-auto w-full max-w-[19rem] sm:max-w-[21rem]">
          <Phone>
            {step === 0 && <ScreenPaste />}
            {step === 1 && <ScreenChecking />}
            {step === 2 && <ScreenVerdict />}
          </Phone>
        </div>

        {/* The steps, as a legend rather than as three more phones. */}
        <ol className="flex flex-col gap-1">
          {STEPS.map((s, i) => (
            <li
              key={s.label}
              className={cn(
                'border-l-2 py-4 pl-5 transition-colors duration-500 motion-reduce:transition-none',
                i === step ? 'border-violet' : 'border-line',
              )}
            >
              <p
                className={cn(
                  'text-page font-medium transition-colors duration-500 motion-reduce:transition-none',
                  i === step ? 'text-ink' : 'text-faint',
                )}
              >
                {s.label}
              </p>
              <p
                className={cn(
                  'mt-1 text-[0.9375rem] transition-colors duration-500 motion-reduce:transition-none',
                  i === step ? 'text-graphite' : 'text-faint',
                )}
              >
                {s.caption}
              </p>
            </li>
          ))}
        </ol>
      </div>

      <Disclosure className="mt-10">
        Illustrative interface and analysis. Not a real product, price or recommendation.
      </Disclosure>
    </Section>
  )
}

/** The device. Deliberately minimal — a rounded slab, no fake OS furniture. */
function Phone({ children }: { children: React.ReactNode }) {
  return (
    <div className="shadow-lift rounded-[2.25rem] border-[7px] border-[#15141d] bg-[#15141d]">
      <div className="bg-paper relative aspect-[9/19] w-full overflow-hidden rounded-[1.75rem]">
        {children}
      </div>
    </div>
  )
}

function ScreenPaste() {
  return (
    <div className="anim-land flex h-full flex-col gap-4 px-5 pt-12">
      <p className="text-ink font-serif text-[1.5rem] leading-tight">Is it worth your money?</p>

      <div className="border-violet flex items-center gap-2 rounded-full border bg-white px-3 py-2.5 shadow-[0_0_0_4px_var(--color-violet-wash)]">
        <span className="text-ink truncate text-[0.75rem]">example.com/checkout…</span>
        <span className="bg-violet ml-auto shrink-0 rounded-full px-3 py-1.5 text-[0.6875rem] font-semibold text-white">
          Analyze
        </span>
      </div>
      <p className="text-graphite text-[0.6875rem]">No link? Upload a screenshot.</p>

      <span className="label text-faint mt-3">Recent</span>
      <div className="flex flex-col gap-2">
        {[
          ['82', 'Design tool, team seats', 'text-buy'],
          ['28', 'Online course', 'text-skip'],
        ].map(([score, name, tone]) => (
          <div
            key={name}
            className="border-line flex items-center gap-2.5 rounded-xl border bg-white px-3 py-2.5"
          >
            <span className={cn('tnum text-[0.875rem] font-semibold', tone)}>{score}</span>
            <span className="text-graphite truncate text-[0.75rem]">{name}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ScreenChecking() {
  return (
    <div className="anim-land flex h-full flex-col gap-4 px-5 pt-12">
      <p className="text-ink font-serif text-[1.375rem] leading-tight">Reading the checkout…</p>

      <div className="bg-line h-1 overflow-hidden rounded-full">
        <div className="bg-violet h-full w-1/2 rounded-full" />
      </div>

      <ul className="mt-2 flex flex-col gap-3">
        {[
          ['Price', true],
          ['Fees', true],
          ['Reviews', true],
          ['Trust', false],
          ['Risk', false],
          ['Alternatives', false],
        ].map(([name, done]) => (
          <li key={String(name)} className="flex items-center gap-2.5">
            <span
              aria-hidden
              className={cn(
                'flex size-4 items-center justify-center rounded-full text-[0.5rem] text-white',
                done ? 'bg-violet' : 'border-line border bg-transparent',
              )}
            >
              {done ? '✓' : ''}
            </span>
            <span className={cn('text-[0.8125rem]', done ? 'text-ink' : 'text-faint')}>{name}</span>
          </li>
        ))}
      </ul>

      <span className="label text-faint mt-3">Found so far</span>
      <div className="flex flex-col gap-2">
        {[
          ['€115', 'in fees at checkout'],
          ['€724', 'the same thing elsewhere'],
        ].map(([v, k]) => (
          <div
            key={k}
            className="border-line flex items-baseline gap-2 rounded-xl border bg-white px-3 py-2.5"
          >
            <span className="tnum text-ink text-[0.875rem] font-semibold">{v}</span>
            <span className="text-graphite text-[0.6875rem]">{k}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ScreenVerdict() {
  return (
    <div className="anim-land flex h-full flex-col gap-3 px-5 pt-12">
      <span className="label text-faint">Worth verdict</span>

      <p className="tnum text-think flex items-baseline gap-1">
        <span className="text-[3.5rem] leading-none font-semibold tracking-[-0.05em]">68</span>
        <span className="text-faint text-[0.75rem]">/100</span>
      </p>
      <p className="text-think text-[1.25rem] leading-none font-semibold tracking-[-0.02em] uppercase">
        Think twice
      </p>

      <p className="text-ink mt-1 font-serif text-[1.0625rem] leading-snug">
        The deal looks good at first. The actual cost changes the picture.
      </p>

      <div className="bg-buy-wash mt-2 flex items-baseline gap-2 rounded-xl px-3 py-3">
        <span className="tnum text-faint text-[0.75rem] line-through">€1,007</span>
        <span className="tnum text-ink text-[1.125rem] font-semibold">€724</span>
        <span className="tnum text-buy ml-auto text-[0.8125rem] font-semibold">−€283</span>
      </div>

      <span className="label text-faint mt-2">Why</span>
      <ul className="flex flex-col gap-2">
        {[
          ['Fees', '€115 at checkout', 'bg-skip'],
          ['Reviews', '4.5 · 1,284', 'bg-buy'],
          ['Trust', 'Established seller', 'bg-buy'],
          ['Risk', 'Locked in at 14 days', 'bg-skip'],
        ].map(([k, v, dot]) => (
          <li key={String(k)} className="flex items-center gap-2 text-[0.75rem]">
            <span aria-hidden className={cn('size-1.5 shrink-0 rounded-full', dot)} />
            <span className="text-ink font-medium">{k}</span>
            <span className="text-graphite truncate">· {v}</span>
          </li>
        ))}
      </ul>

      <div className="bg-violet mt-auto mb-5 rounded-full py-3 text-center text-[0.8125rem] font-semibold text-white">
        Share this verdict
      </div>
    </div>
  )
}
