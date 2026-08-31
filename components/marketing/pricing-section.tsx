import { Section, Eyebrow, Statement, Disclosure } from './section'
import { PLANS, PRICING_DISCLOSURE, type Plan } from '@/lib/pricing'
import { cn } from '@/lib/utils/cn'

/**
 * Pricing.
 *
 * Real hierarchy rather than three identical boxes: the middle plan is lifted
 * onto midnight with violet lighting and sits proud of the row, and the volume
 * axis is drawn as a scale so the difference between plans is visible before
 * the bullets are read.
 *
 * No prices — they haven't been decided, and a placeholder number would mislead
 * every early visitor. The slot for them is already in the layout.
 */
export function PricingSection({ heading = true }: { heading?: boolean }) {
  return (
    <Section id="pricing" tone="sunk">
      {heading && (
        <div className="max-w-[36rem]">
          <Eyebrow index="10">What it costs</Eyebrow>
          <Statement className="mt-5 max-w-[20ch]">Three plans. All paid.</Statement>
          <p className="text-lead text-graphite mt-6">
            Worth catches a €283 overpayment or it doesn’t. That’s a straightforward thing to charge
            for — so there’s no free tier, and no ad money quietly changing whose side we’re on.
          </p>
        </div>
      )}

      {/* Stretch, not centre: centring three cards of unequal content height
          leaves their tops and their price rows on different baselines, which
          reads as a rendering fault rather than as emphasis. The featured plan
          is lifted by scale instead. */}
      <div className="mt-12 grid grid-cols-1 gap-4 sm:mt-16 lg:grid-cols-3 lg:items-stretch">
        {PLANS.map((plan, index) => (
          <PlanPanel key={plan.id} plan={plan} index={index} />
        ))}
      </div>

      <Disclosure className="text-graphite mt-8 max-w-[62ch] text-[0.8125rem] leading-relaxed">
        {PRICING_DISCLOSURE}
      </Disclosure>
    </Section>
  )
}

function PlanPanel({ plan, index }: { plan: Plan; index: number }) {
  const featured = plan.emphasis

  return (
    <div
      className={cn(
        'rounded-object relative flex flex-col gap-7 border p-6 sm:p-7',
        featured
          ? 'stage-light border-midnight-line bg-midnight shadow-violet text-white lg:scale-[1.04] lg:py-10'
          : 'border-line bg-surface',
      )}
    >
      {featured && (
        <span
          className="bg-violet absolute top-0 left-1/2 h-1 w-24 -translate-x-1/2 rounded-b-full"
          aria-hidden
        />
      )}

      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between gap-3">
          <h3 className={cn('text-heading font-semibold', featured ? 'text-white' : 'text-ink')}>
            {plan.name}
          </h3>
          <span className={cn('tnum label', featured ? 'text-violet-lift' : 'text-faint')}>
            {String(index + 1).padStart(2, '0')}
          </span>
        </div>
        {/* Two lines' worth of room whatever the plan says, so the rule under
            the header lands at the same height in all three cards. */}
        <p
          className={cn(
            'text-[0.9375rem] leading-snug lg:min-h-[2.625rem]',
            featured ? 'text-white/55' : 'text-graphite',
          )}
        >
          {plan.audience}
        </p>
      </div>

      {/* The volume axis, shown rather than described. */}
      <div className="flex items-center gap-1.5" aria-hidden>
        {[0, 1, 2].map((step) => (
          <span
            key={step}
            className={cn(
              'h-1 flex-1 rounded-full',
              step <= index
                ? featured
                  ? 'bg-violet-lift'
                  : 'bg-ink'
                : featured
                  ? 'bg-white/12'
                  : 'bg-line',
            )}
          />
        ))}
      </div>

      <div className={cn('border-y py-5', featured ? 'border-white/10' : 'border-line')}>
        <span className={cn('label', featured ? 'text-white/40' : 'text-graphite')}>Price</span>
        <p className={cn('mt-2.5 text-xl font-medium', featured ? 'text-white/45' : 'text-faint')}>
          To be confirmed
        </p>
      </div>

      <ul className="flex flex-col gap-3">
        {plan.includes.map((item) => (
          <li
            key={item}
            className={cn(
              'flex items-start gap-2.5 text-[0.9375rem] leading-snug',
              featured ? 'text-white/75' : 'text-ink-soft',
            )}
          >
            <span
              className={cn(
                'mt-[7px] size-1.5 shrink-0 rounded-full',
                featured ? 'bg-violet-lift' : 'bg-line-strong',
              )}
              aria-hidden
            />
            {item}
          </li>
        ))}
      </ul>
    </div>
  )
}
