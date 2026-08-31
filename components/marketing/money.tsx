import { Section, SectionLabel, SectionTitle } from './section'
import { Reveal } from './reveal'
import { formatMoney } from '@/lib/analysis/format'
import { SHARE_EXAMPLE } from '@/lib/analysis/fixtures'

/**
 * The money.
 *
 * Worth's clearest value statement, told in three figures rather than a claim.
 * These are illustrative — Worth has no real user data and does not pretend to.
 */
export function Money() {
  const price = formatMoney(SHARE_EXAMPLE.priceMinor, SHARE_EXAMPLE.currency)
  const best = formatMoney(SHARE_EXAMPLE.bestPriceMinor, SHARE_EXAMPLE.currency)
  const saving = formatMoney(
    (SHARE_EXAMPLE.priceMinor ?? 0) - (SHARE_EXAMPLE.bestPriceMinor ?? 0),
    SHARE_EXAMPLE.currency,
  )

  return (
    <Section bleed>
      <div className="flex flex-col gap-3">
        <SectionLabel>The money</SectionLabel>
        <SectionTitle className="max-w-[20ch]">The point is what you don’t spend.</SectionTitle>
      </div>

      <div className="rounded-card border-rule bg-rule mt-10 grid grid-cols-1 gap-px overflow-hidden border sm:mt-14 sm:grid-cols-3">
        <Figure label="You were about to spend" value={price} delay={0} />
        <Figure label="Worth found" value={best} delay={110} />
        <Figure label="Potential saving" value={saving} delay={220} tone="saving" />
      </div>

      <p className="text-muted mt-4 text-[0.8125rem]">
        An illustrative example. Worth makes no claim about savings by real users — it has none yet.
      </p>
    </Section>
  )
}

function Figure({
  label,
  value,
  delay,
  tone,
}: {
  label: string
  value: string | null
  delay: number
  tone?: 'saving'
}) {
  if (!value) return null
  return (
    <div className="bg-surface px-5 py-8 sm:px-6 sm:py-10">
      <Reveal delay={delay}>
        <p className="text-muted text-[0.6875rem] font-medium tracking-[0.14em] uppercase">
          {label}
        </p>
        <p
          className={`tnum text-figure mt-2 font-semibold ${
            tone === 'saving' ? 'text-buy' : 'text-ink'
          }`}
        >
          {value}
        </p>
      </Reveal>
    </div>
  )
}
