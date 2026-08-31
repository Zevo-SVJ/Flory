import { Section, Eyebrow, Statement } from './section'
import { cn } from '@/lib/utils/cn'

/**
 * Beat 09 — three reasons, each with the thing it's talking about beside it.
 *
 * Large numbered rows rather than a three-icon grid: each reason gets a
 * demonstration rather than a glyph, and the rows alternate side so the
 * section doesn't read as a list.
 */
export function WhyWorth() {
  return (
    <Section>
      <div className="max-w-[34rem]">
        <Eyebrow index="09">Why bother</Eyebrow>
        <Statement className="mt-5 max-w-[18ch]">Three reasons it earns its place.</Statement>
      </div>

      <div className="divide-line mt-14 flex flex-col divide-y sm:mt-20">
        <Reason
          index="01"
          title="Stop opening fifteen tabs"
          body="Worth does the comparison shopping, the review reading and the seller checking in one pass, and hands you the part you were looking for."
        >
          <TabStack />
        </Reason>

        <Reason
          index="02"
          title="Know what you’re actually paying for"
          body="Not a star rating. What the money buys, what buyers keep complaining about, and whether the seller stands behind it."
          flip
        >
          <ValueBars />
        </Reason>

        <Reason
          index="03"
          title="Find the better option"
          body="Worth doesn’t just judge the thing in front of you. It goes looking for the same thing cheaper, and the better thing at the same price."
        >
          <BetterOption />
        </Reason>
      </div>
    </Section>
  )
}

function Reason({
  index,
  title,
  body,
  children,
  flip,
}: {
  index: string
  title: string
  body: string
  children: React.ReactNode
  flip?: boolean
}) {
  return (
    <div className="grid grid-cols-1 items-center gap-8 py-12 sm:py-16 lg:grid-cols-2 lg:gap-16">
      <div className={cn(flip && 'lg:order-2')}>
        <span className="tnum label text-violet">{index}</span>
        <h3 className="text-heading text-ink mt-4 font-serif font-medium sm:text-3xl">{title}</h3>
        <p className="text-lead text-graphite mt-4 max-w-[42ch]">{body}</p>
      </div>
      <div className={cn(flip && 'lg:order-1')}>{children}</div>
    </div>
  )
}

/* Fifteen tabs collapsing into one answer. */
function TabStack() {
  return (
    <div className="relative" aria-hidden>
      <div className="flex flex-col gap-1.5">
        {[
          'forum thread · 2023',
          'retailer B · €389',
          '18 min video review',
          'retailer C · out of stock',
          'comparison blog',
        ].map((tab, i) => (
          <div
            key={tab}
            className="border-line bg-surface flex items-center gap-2.5 rounded-lg border px-3 py-2.5"
            style={{ opacity: 1 - i * 0.16 }}
          >
            <span className="bg-line-strong size-1.5 shrink-0 rounded-full" />
            <span className="text-graphite truncate text-[0.8125rem]">{tab}</span>
          </div>
        ))}
      </div>
      <div className="from-paper pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t to-transparent" />
      <div className="border-violet-line bg-violet-wash relative -mt-4 flex items-center gap-3 rounded-lg border px-4 py-3">
        <span className="tnum text-ink text-xl font-semibold">61</span>
        <span className="text-think text-[0.875rem] font-medium">Think twice</span>
        <span className="text-graphite ml-auto text-[0.8125rem]">1 answer</span>
      </div>
    </div>
  )
}

/* What the money buys, broken out. */
function ValueBars() {
  const rows: Array<[string, number, 'buy' | 'think']> = [
    ['Noise cancelling', 92, 'buy'],
    ['Battery', 88, 'buy'],
    ['Build quality', 74, 'buy'],
    ['Case design', 41, 'think'],
    ['Price for spec', 34, 'think'],
  ]
  return (
    <div
      className="rounded-object border-line bg-surface flex flex-col gap-3.5 border p-5 sm:p-6"
      aria-hidden
    >
      {rows.map(([label, value, tone]) => (
        <div key={label} className="flex items-center gap-4">
          <span className="text-graphite w-28 shrink-0 text-[0.8125rem] sm:w-32">{label}</span>
          <span className="bg-paper-2 h-1.5 flex-1 overflow-hidden rounded-full">
            <span
              className={cn('block h-full rounded-full', tone === 'buy' ? 'bg-buy' : 'bg-think')}
              style={{ width: `${value}%` }}
            />
          </span>
        </div>
      ))}
    </div>
  )
}

/* The alternative, found. */
function BetterOption() {
  return (
    <div className="flex flex-col gap-2.5" aria-hidden>
      <div className="rounded-object border-line bg-surface flex items-center justify-between gap-4 border px-5 py-4 opacity-60">
        <div>
          <p className="text-ink text-[0.9375rem] font-medium">What you were looking at</p>
          <p className="text-graphite text-[0.8125rem]">This seller</p>
        </div>
        <span className="tnum text-faint text-2xl font-semibold line-through decoration-1">
          €399
        </span>
      </div>
      <div className="rounded-object border-buy/25 bg-buy-wash flex items-center justify-between gap-4 border px-5 py-4">
        <div>
          <p className="text-ink text-[0.9375rem] font-medium">Same model, verified retailer</p>
          <p className="text-graphite text-[0.8125rem]">Same warranty and returns</p>
        </div>
        <span className="tnum text-buy text-2xl font-semibold">€329</span>
      </div>
      <div className="rounded-object border-line bg-surface flex items-center justify-between gap-4 border px-5 py-4">
        <div>
          <p className="text-ink text-[0.9375rem] font-medium">Comparable, lighter</p>
          <p className="text-graphite text-[0.8125rem]">Same NC tier, no case</p>
        </div>
        <span className="tnum text-ink text-2xl font-semibold">€299</span>
      </div>
    </div>
  )
}
