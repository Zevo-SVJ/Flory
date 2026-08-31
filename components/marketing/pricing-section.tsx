import { Section, Beat } from './section'
import { PLANS, PRICING_DISCLOSURE, type Plan } from '@/lib/pricing'
import { cn } from '@/lib/utils/cn'

/**
 * Pricing.
 *
 * Three plans with a real hierarchy rather than three identical white boxes:
 * the middle plan is inverted onto ink with a Worth Blue edge, and the volume
 * axis is stated as a scale row so the difference between plans is visible
 * before the bullets are read.
 *
 * No prices — they haven't been decided, and a placeholder number would be a
 * lie to every early visitor. The layout already has the slot for them.
 */
export function PricingSection({ heading = true }: { heading?: boolean }) {
  return (
    <Section id="pricing">
      {heading && (
        <div className="flex flex-col gap-3">
          <Beat index="07">What it costs</Beat>
          <h2 className="text-statement text-ink max-w-[24ch] font-serif font-medium">
            Three plans. All paid. None of them priced yet.
          </h2>
          <p className="text-lead text-graphite mt-2 max-w-[48ch]">
            Worth catches a €70 overpayment or it doesn’t. That’s a straightforward thing to charge
            for, so there’s no free tier and no ad money changing whose side we’re on.
          </p>
        </div>
      )}

      <div className="mt-10 grid grid-cols-1 gap-3 sm:mt-14 lg:grid-cols-3">
        {PLANS.map((plan, index) => (
          <PlanPanel key={plan.id} plan={plan} index={index} />
        ))}
      </div>

      <p className="text-graphite mt-6 max-w-[62ch] text-[0.8125rem] leading-relaxed">
        {PRICING_DISCLOSURE}
      </p>
    </Section>
  )
}

function PlanPanel({ plan, index }: { plan: Plan; index: number }) {
  const emphasis = plan.emphasis

  return (
    <div
      className={cn(
        'rounded-object relative flex flex-col gap-6 border p-6',
        emphasis ? 'border-ink bg-ink text-white lg:-my-3 lg:py-9' : 'border-line bg-surface',
      )}
    >
      {emphasis && (
        <span className="rounded-t-object bg-worth absolute inset-x-0 top-0 h-1" aria-hidden />
      )}

      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between gap-3">
          <h3 className={cn('text-heading font-semibold', emphasis ? 'text-white' : 'text-ink')}>
            {plan.name}
          </h3>
          <span className={cn('tnum label', emphasis ? 'text-worth' : 'text-faint')}>
            {String(index + 1).padStart(2, '0')}
          </span>
        </div>
        <p
          className={cn(
            'text-[0.9375rem] leading-snug',
            emphasis ? 'text-white/60' : 'text-graphite',
          )}
        >
          {plan.audience}
        </p>
      </div>

      {/* The volume axis, shown rather than described. */}
      <div className="flex items-center gap-1" aria-hidden>
        {[0, 1, 2].map((step) => (
          <span
            key={step}
            className={cn(
              'h-1 flex-1 rounded-full',
              step <= index
                ? emphasis
                  ? 'bg-worth'
                  : 'bg-ink'
                : emphasis
                  ? 'bg-white/15'
                  : 'bg-line',
            )}
          />
        ))}
      </div>

      <div className={cn('border-y py-4', emphasis ? 'border-white/12' : 'border-line')}>
        <span className={cn('label', emphasis ? 'text-white/45' : 'text-graphite')}>Price</span>
        <p className={cn('mt-2 text-lg font-medium', emphasis ? 'text-white/50' : 'text-faint')}>
          To be confirmed
        </p>
      </div>

      <ul className="flex flex-col gap-2.5">
        {plan.includes.map((item) => (
          <li
            key={item}
            className={cn(
              'flex items-start gap-2.5 text-[0.9375rem] leading-snug',
              emphasis ? 'text-white/80' : 'text-ink-soft',
            )}
          >
            <span
              className={cn(
                'mt-[7px] size-1.5 shrink-0 rounded-full',
                emphasis ? 'bg-worth' : 'bg-line-strong',
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
