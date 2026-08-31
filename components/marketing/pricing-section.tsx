import { Section, SectionLabel, SectionTitle } from './section'
import { Card } from '@/components/ui/card'
import { PLANS, PRICING_DISCLOSURE, type Plan } from '@/lib/pricing'
import { cn } from '@/lib/utils/cn'

/**
 * Three paid plans, no prices.
 *
 * The shape is real so the eventual Stripe integration slots in without a
 * redesign. The numbers are absent because they have not been decided, and
 * inventing them would be fake.
 */
export function PricingSection({ heading = true }: { heading?: boolean }) {
  return (
    <Section id="pricing">
      {heading && (
        <div className="flex flex-col gap-3">
          <SectionLabel>Pricing</SectionLabel>
          <SectionTitle className="max-w-[24ch]">
            Three plans. All paid. None of them priced yet.
          </SectionTitle>
        </div>
      )}

      <div className="mt-10 grid grid-cols-1 gap-4 sm:mt-14 lg:grid-cols-3">
        {PLANS.map((plan) => (
          <PlanCard key={plan.id} plan={plan} />
        ))}
      </div>

      <p className="text-muted mt-6 max-w-[62ch] text-[0.8125rem] leading-relaxed">
        {PRICING_DISCLOSURE}
      </p>
    </Section>
  )
}

function PlanCard({ plan }: { plan: Plan }) {
  return (
    <Card className={cn('flex flex-col gap-5 p-6', plan.emphasis && 'border-ink')}>
      <div className="flex flex-col gap-1.5">
        <h3 className="text-heading text-ink font-semibold">{plan.name}</h3>
        <p className="text-muted text-[0.9375rem] leading-snug">{plan.audience}</p>
      </div>

      <div className="border-rule border-y py-4">
        <p className="text-muted text-[0.6875rem] font-medium tracking-[0.14em] uppercase">Price</p>
        <p className="text-faint mt-1.5 text-lg font-medium">To be confirmed</p>
      </div>

      <ul className="flex flex-col gap-2">
        {plan.includes.map((item) => (
          <li key={item} className="text-ink-2 flex items-start gap-2.5 text-[0.9375rem]">
            <span className="bg-faint mt-2 size-1.5 shrink-0 rounded-full" aria-hidden />
            {item}
          </li>
        ))}
      </ul>
    </Card>
  )
}
