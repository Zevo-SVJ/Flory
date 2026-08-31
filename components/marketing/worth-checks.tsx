import { Section, Eyebrow, Statement, Disclosure } from './section'
import { cn } from '@/lib/utils/cn'

/**
 * Beat 03 — the six dimensions, shown as findings.
 *
 * Not a feature grid. Each module holds the actual output of one check, and
 * the spans are uneven because the dimensions aren't equally weighted: price
 * and alternatives drive this verdict, so they take the most room. A visitor
 * scanning without reading should come away with "it gathered all this".
 */

export function WorthChecks() {
  return (
    <Section id="how-it-works">
      <div className="max-w-[34rem]">
        <Eyebrow index="03">Worth checks</Eyebrow>
        <Statement className="mt-5 max-w-[18ch]">Worth checks the details.</Statement>
        <p className="text-lead text-graphite mt-6">
          Eleven sellers, two thousand reviews, the warranty, the returns policy and every
          comparable option — in about a minute.
        </p>
      </div>

      <div className="mt-12 grid grid-cols-1 gap-3 sm:mt-16 sm:grid-cols-2 lg:grid-cols-3">
        {/* Price — the finding that drives this verdict, so it leads and spans. */}
        <Module label="Price" meta="11 sellers" accent className="sm:col-span-2">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-2">
            <span className="tnum text-faint text-3xl font-medium line-through decoration-1 sm:text-4xl">
              €399
            </span>
            <Arrow />
            <span className="tnum text-ink text-3xl font-semibold tracking-[-0.035em] sm:text-4xl">
              €329
            </span>
            <span className="tnum bg-buy-wash text-buy rounded-full px-2.5 py-1 text-[0.8125rem] font-semibold">
              Save €70
            </span>
          </div>
          <p className="text-graphite mt-3 text-[0.875rem]">
            Same model, verified retailer, same two-year warranty.
          </p>
        </Module>

        <Module label="Value">
          <ul className="flex flex-col gap-2 text-[0.875rem]">
            <Spec k="Noise cancelling" v="Best in class" tone="buy" />
            <Spec k="Battery" v="30 h" tone="buy" />
            <Spec k="Case" v="Bulkier than before" tone="think" />
          </ul>
        </Module>

        <Module label="Reviews" meta="2,140 read" className="sm:col-span-2">
          <div className="flex flex-col gap-3">
            <Quote tone="buy">“Battery life is genuinely 30 hours.”</Quote>
            <Quote tone="think">“The case is bulkier than the last generation.”</Quote>
          </div>
        </Module>

        <Module label="Trust">
          <ul className="flex flex-col gap-2">
            <Check>Verified seller</Check>
            <Check>30-day returns</Check>
            <Check>2-year warranty</Check>
          </ul>
        </Module>

        <Module label="Risk" tone="think">
          <p className="text-ink-soft text-[0.9375rem] leading-snug">
            A refresh is expected within about six months.
          </p>
          <p className="text-graphite mt-2 text-[0.8125rem]">
            The last two generations ran on an 18-month cycle.
          </p>
        </Module>

        <Module label="Alternatives" tone="buy" className="sm:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="min-w-0">
              <p className="text-ink font-medium">Comparable option</p>
              <p className="text-graphite text-[0.875rem]">
                Same noise-cancelling tier, lighter, no case
              </p>
            </div>
            <span className="tnum text-buy text-3xl font-semibold">€299</span>
          </div>
        </Module>
      </div>

      <Disclosure className="mt-6">
        Illustrative evidence. Real analyses will cite a source for every line.
      </Disclosure>
    </Section>
  )
}

/**
 * An evidence module: flat, squared, hairline-bordered — a filed finding
 * rather than a UI card. The corner label names the dimension.
 */
function Module({
  label,
  meta,
  accent,
  tone,
  children,
  className,
}: {
  label: string
  meta?: string
  accent?: boolean
  tone?: 'buy' | 'think'
  children: React.ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        'rounded-object flex flex-col gap-4 border p-5 sm:p-6',
        accent ? 'border-violet-line bg-violet-wash' : 'border-line bg-surface',
        tone === 'buy' && 'border-buy/20 bg-buy-wash/40',
        tone === 'think' && 'border-think/25 bg-think-wash/40',
        className,
      )}
    >
      <div className="flex items-baseline justify-between gap-3">
        <span className={cn('label', accent ? 'text-violet-deep' : 'text-graphite')}>{label}</span>
        {meta && <span className="tnum text-faint text-[0.6875rem]">{meta}</span>}
      </div>
      <div className="min-w-0">{children}</div>
    </div>
  )
}

function Spec({ k, v, tone }: { k: string; v: string; tone: 'buy' | 'think' }) {
  return (
    <li className="flex justify-between gap-3">
      <span className="text-graphite">{k}</span>
      <span className={cn('font-medium', tone === 'buy' ? 'text-buy' : 'text-think')}>{v}</span>
    </li>
  )
}

function Quote({ children, tone }: { children: React.ReactNode; tone: 'buy' | 'think' }) {
  return (
    <blockquote
      className={cn(
        'text-ink border-l-2 pl-3.5 font-serif text-[1.0625rem] leading-snug',
        tone === 'buy' ? 'border-buy/45' : 'border-think/45',
      )}
    >
      {children}
    </blockquote>
  )
}

function Check({ children }: { children: React.ReactNode }) {
  return (
    <li className="text-ink-soft flex items-start gap-2.5 text-[0.9375rem]">
      <span
        className="bg-buy/12 text-buy mt-[3px] flex size-4 shrink-0 items-center justify-center rounded-[3px]"
        aria-hidden
      >
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
          <path
            d="m1.6 5.2 2.2 2.2L8.4 2.8"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="square"
          />
        </svg>
      </span>
      {children}
    </li>
  )
}

function Arrow() {
  return (
    <svg
      width="24"
      height="13"
      viewBox="0 0 22 12"
      fill="none"
      aria-hidden
      className="shrink-0 self-center"
    >
      <path
        d="M0 6h19M14.5 1.5 19.5 6l-5 4.5"
        stroke="var(--color-violet)"
        strokeWidth="1.9"
        strokeLinecap="square"
      />
    </svg>
  )
}
