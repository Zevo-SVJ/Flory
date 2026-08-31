import { Section, Eyebrow, Statement, Disclosure } from './section'
import { CheckoutSurface } from '@/components/worth/checkout-surface'
import { cn } from '@/lib/utils/cn'
import type { Verdict } from '@/lib/analysis/types'

/**
 * Beat 04 — Worth is not a retail price checker.
 *
 * Three genuinely different kinds of spend, each given its own full-width
 * moment down the page and each drawn in the visual language of the thing
 * being analysed: a checkout, a seat-based plan, a course landing page. The
 * argument of this section is that the language changes — so giving all three
 * the same card would have contradicted it.
 *
 * No photography here on purpose. All three of these are bought on a screen,
 * and a photograph of a physical object would have said the opposite.
 *
 * One of the three is a Buy, so Worth doesn't read as reflexively negative.
 */

const VERDICT_STYLE: Record<Verdict, { text: string; label: string }> = {
  buy: { text: 'text-buy', label: 'Buy' },
  think_twice: { text: 'text-think', label: 'Think twice' },
  skip: { text: 'text-skip', label: 'Skip' },
}

export function PurchaseTypes() {
  return (
    <Section tone="sunk" width="wide">
      <div className="max-w-[34rem]">
        <Eyebrow index="06">Anywhere you spend</Eyebrow>
        <Statement className="mt-5 max-w-[18ch]">A link is a link.</Statement>
        <p className="text-lead text-graphite mt-6">
          Worth doesn’t care whether it’s a checkout, a subscription or a course someone sold you
          on TikTok. If money is about to leave your account, it can read it.
        </p>
      </div>

      <div className="mt-14 flex flex-col gap-16 sm:mt-20 sm:gap-24">
        <Moment
          kind="Checkout"
          title="Annual plan, paid upfront"
          meta="Fees added at the last step"
          score={68}
          verdict="think_twice"
          line="Fine service. The advertised price isn’t the price you pay."
          price="€1,007"
          best="€724"
        >
          <CheckoutSurface
            meta="Order summary"
            title="Annual plan, paid upfront"
            lines={[
              { label: 'Advertised', amount: '€892' },
              { label: 'Platform fee', amount: '+ €84', late: true },
              { label: 'Onboarding add-on', amount: '+ €31', late: true },
            ]}
            total="€1,007"
          />
        </Moment>

        <Moment
          kind="Software"
          title="Design tool, team seats"
          meta="Per seat, billed yearly"
          score={82}
          verdict="buy"
          line="Priced fairly for the seats you actually use, and easy to leave."
          price="€96/yr"
          best={null}
          flip
        >
          <SeatsScene />
        </Moment>

        <Moment
          kind="Digital product"
          title="“Six-figure freelancing”"
          meta="Online course · 14 modules"
          score={28}
          verdict="skip"
          line="The outcome claims aren’t backed by anything a buyer can check."
          price="€249"
          best={null}
        >
          <CourseScene />
        </Moment>
      </div>

      <Disclosure className="mt-14">
        Illustrative examples. Not real analyses, prices, products or recommendations.
      </Disclosure>
    </Section>
  )
}

function Moment({
  kind,
  title,
  meta,
  score,
  verdict,
  line,
  price,
  best,
  flip,
  children,
}: {
  kind: string
  title: string
  meta: string
  score: number
  verdict: Verdict
  line: string
  price: string
  best: string | null
  flip?: boolean
  children: React.ReactNode
}) {
  const style = VERDICT_STYLE[verdict]

  return (
    <article className="grid grid-cols-1 items-center gap-8 lg:grid-cols-2 lg:gap-16">
      <div className={cn('mx-auto w-full max-w-[26rem] lg:max-w-none', flip && 'lg:order-2')}>
        {children}
      </div>

      <div className={cn(flip && 'lg:order-1')}>
        <span className="label text-faint">{kind}</span>
        <p className="text-page text-ink mt-4 max-w-[20ch] font-medium">{title}</p>
        <p className="text-graphite mt-2 text-[0.9375rem]">{meta}</p>

        <div className="mt-8 flex items-baseline gap-4">
          <span className={cn('tnum text-figure font-semibold', style.text)}>{score}</span>
          <span className="flex flex-col">
            <span className={cn('text-page font-semibold tracking-[-0.02em]', style.text)}>
              {style.label}
            </span>
            <span className="tnum text-faint text-[0.8125rem]">out of 100</span>
          </span>
        </div>

        <p className="text-lead text-ink-soft mt-6 max-w-[36ch]">{line}</p>

        <div className="border-line mt-6 flex items-baseline gap-3 border-t pt-5">
          <span
            className={cn(
              'tnum text-figure-sm font-semibold',
              best ? 'text-faint line-through decoration-1' : 'text-ink',
            )}
          >
            {price}
          </span>
          {best && (
            <>
              <span aria-hidden className="text-violet">
                →
              </span>
              <span className="tnum text-figure-sm text-ink font-semibold">{best}</span>
            </>
          )}
        </div>
      </div>
    </article>
  )
}

/** Software shown as a seat-based plan: the shape of the actual decision. */
function SeatsScene() {
  return (
    <div className="bg-midnight rounded-object relative overflow-hidden">
      <div className="stage-light absolute inset-0" aria-hidden />
      <div className="relative flex flex-col justify-center gap-4 p-6 sm:p-10">
        <span className="label text-white/40">Team plan</span>

        <p className="tnum text-figure font-semibold text-white">
          €8<span className="ml-1 text-[0.28em] font-normal text-white/40">per seat / month</span>
        </p>

        <ul className="mt-2 flex flex-col gap-2.5">
          {['12 seats active', '3 seats unused for 90 days', 'Cancel any time'].map((row, i) => (
            <li key={row} className="flex items-center gap-2.5 text-[0.9375rem] text-white/70">
              <span
                aria-hidden
                className={cn('size-1.5 rounded-full', i === 1 ? 'bg-think-lift' : 'bg-buy-lift')}
              />
              {row}
            </li>
          ))}
        </ul>

        <div className="mt-4 flex items-center justify-between border-t border-white/10 pt-4">
          <span className="text-[0.8125rem] text-white/45">Billed annually</span>
          <span className="tnum text-[1.125rem] font-semibold text-white">€96/yr</span>
        </div>
      </div>
    </div>
  )
}

/** A course shown the way courses are actually sold: promises, then a price. */
function CourseScene() {
  return (
    <div className="rounded-object border-line bg-surface shadow-object overflow-hidden border">
      <div className="bg-ink px-6 py-8 sm:px-8 sm:py-10">
        <p className="font-serif text-[1.5rem] leading-tight font-medium text-white sm:text-[1.75rem]">
          Six-figure freelancing
        </p>
        <p className="mt-3 text-[0.9375rem] text-white/55">14 modules · lifetime access</p>
      </div>

      <ul className="flex flex-col gap-3 px-6 py-6 sm:px-8">
        {[
          'Replace your salary in 90 days',
          'The exact scripts I used',
          'No experience required',
        ].map((claim) => (
          <li key={claim} className="flex items-start gap-2.5 text-[0.9375rem]">
            <span aria-hidden className="bg-skip mt-2 size-1.5 shrink-0 rounded-full" />
            <span className="text-graphite">{claim}</span>
          </li>
        ))}
      </ul>

      <div className="border-line flex items-center justify-between border-t px-6 py-5 sm:px-8">
        <span className="tnum text-ink text-[1.5rem] font-semibold">€249</span>
        <span className="bg-ink rounded-full px-5 py-2.5 text-[0.8125rem] font-semibold text-white">
          Enrol now
        </span>
      </div>
    </div>
  )
}
