import { Section, SectionLabel, SectionTitle } from './section'
import { Reveal } from './reveal'
import { Card } from '@/components/ui/card'
import { SIGNAL_LABEL, SIGNAL_QUESTION } from '@/lib/analysis/verdict'
import type { SignalKind } from '@/lib/analysis/types'
import type { ReactNode } from 'react'

/**
 * What Worth checks.
 *
 * Not a six-icon feature grid. Each dimension is shown as the evidence fragment
 * it will actually produce, so the section demonstrates the output rather than
 * advertising a capability.
 */
export function Dimensions() {
  return (
    <Section bleed>
      <div className="flex flex-col gap-3">
        <SectionLabel>What Worth checks</SectionLabel>
        <SectionTitle className="max-w-[22ch]">Six questions, answered with evidence.</SectionTitle>
      </div>

      <div className="mt-10 grid grid-cols-1 gap-4 sm:mt-14 sm:grid-cols-2 lg:grid-cols-3">
        <Fragment kind="price" delay={0}>
          <div className="flex items-baseline gap-3">
            <span className="tnum text-ink text-2xl font-semibold">€179</span>
            <span className="tnum text-muted decoration-skip/50 text-lg line-through">€99–129</span>
          </div>
          <p className="text-muted mt-2 text-[0.8125rem]">
            Four other retailers carry the same model for less.
          </p>
        </Fragment>

        <Fragment kind="value" delay={70}>
          <ul className="flex flex-col gap-1.5 text-[0.8125rem]">
            <li className="flex justify-between gap-3">
              <span className="text-muted">Noise cancelling</span>
              <span className="text-think font-medium">Tier 2 of 4</span>
            </li>
            <li className="flex justify-between gap-3">
              <span className="text-muted">Build</span>
              <span className="text-skip font-medium">Plastic hinge</span>
            </li>
            <li className="flex justify-between gap-3">
              <span className="text-muted">Battery</span>
              <span className="text-buy font-medium">32 h</span>
            </li>
          </ul>
        </Fragment>

        <Fragment kind="reviews" delay={140}>
          <blockquote className="border-skip/40 text-ink-2 border-l-2 pl-3 font-serif text-[0.9375rem] leading-snug">
            “The hinge cracked after about ten months.”
          </blockquote>
          <p className="text-muted mt-2 text-[0.8125rem]">
            Mentioned in 34 of 210 long-term reviews.
          </p>
        </Fragment>

        <Fragment kind="trust" delay={0}>
          <div className="flex flex-col gap-1.5 text-[0.8125rem]">
            <div className="flex items-center gap-2">
              <span className="bg-buy size-1.5 rounded-full" aria-hidden />
              <span className="text-muted">Trading since 2014</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="bg-buy size-1.5 rounded-full" aria-hidden />
              <span className="text-muted">30-day returns, buyer pays postage</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="bg-think size-1.5 rounded-full" aria-hidden />
              <span className="text-muted">No published warranty terms</span>
            </div>
          </div>
        </Fragment>

        <Fragment kind="risk" delay={70}>
          <div className="rounded-input border-think/25 bg-think-soft border px-3 py-2.5">
            <p className="text-think text-[0.8125rem] font-medium">Listing changed recently</p>
            <p className="text-muted mt-1 text-[0.8125rem]">
              Reviews were carried over from a different model.
            </p>
          </div>
        </Fragment>

        <Fragment kind="alternative" delay={140}>
          <div className="rounded-input border-buy/25 bg-buy-soft flex items-center justify-between gap-3 border px-3 py-2.5">
            <div className="min-w-0">
              <p className="text-ink truncate text-[0.8125rem] font-medium">
                Comparable, metal frame
              </p>
              <p className="text-muted text-[0.8125rem]">Same NC tier</p>
            </div>
            <span className="tnum text-buy shrink-0 text-lg font-semibold">€79</span>
          </div>
        </Fragment>
      </div>
    </Section>
  )
}

function Fragment({
  kind,
  delay,
  children,
}: {
  kind: SignalKind
  delay: number
  children: ReactNode
}) {
  return (
    <Reveal delay={delay}>
      <Card className="flex h-full flex-col gap-3 p-5">
        <div>
          <h3 className="text-muted text-[0.6875rem] font-medium tracking-[0.14em] uppercase">
            {SIGNAL_LABEL[kind]}
          </h3>
          <p className="text-ink mt-1 text-[0.9375rem] font-medium">{SIGNAL_QUESTION[kind]}</p>
        </div>
        <div className="border-rule mt-auto border-t pt-3">{children}</div>
      </Card>
    </Reveal>
  )
}
