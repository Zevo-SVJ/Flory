import { cn } from '@/lib/utils/cn'

/**
 * The price drop — Worth's second brand object.
 *
 * "€399 → €329, save €70" is the single most repeatable idea in the product,
 * so it gets one fixed treatment: struck original, blue arrow (the brand
 * *doing* something), destination in ink, saving in verdict green. It appears
 * in the hero, the money moment, the share card and every result.
 *
 * The arrow is Worth Blue rather than green because the arrow represents
 * Worth's finding, not the verdict; only the saving figure carries meaning
 * colour.
 */
export function PriceDrop({
  from,
  to,
  saving,
  size = 'md',
  orientation = 'horizontal',
  className,
}: {
  from: string
  to: string
  saving?: string | null
  size?: 'sm' | 'md' | 'lg'
  orientation?: 'horizontal' | 'stacked'
  className?: string
}) {
  const figure =
    size === 'lg' ? 'text-figure' : size === 'md' ? 'text-[1.75rem] sm:text-4xl' : 'text-xl'
  const struck =
    size === 'lg' ? 'text-3xl sm:text-5xl' : size === 'md' ? 'text-xl sm:text-2xl' : 'text-base'

  if (orientation === 'stacked') {
    return (
      <div className={cn('flex flex-col gap-1', className)}>
        <span className={cn('tnum text-faint font-medium line-through decoration-1', struck)}>
          {from}
        </span>
        <div className="flex items-baseline gap-2">
          <ArrowDown />
          <span className={cn('tnum text-ink font-semibold tracking-[-0.035em]', figure)}>
            {to}
          </span>
        </div>
        {saving && <SavingTag saving={saving} />}
      </div>
    )
  }

  return (
    <div className={cn('flex flex-wrap items-baseline gap-x-3 gap-y-1.5', className)}>
      <span className={cn('tnum text-faint font-medium line-through decoration-1', struck)}>
        {from}
      </span>
      <ArrowRight />
      <span className={cn('tnum text-ink font-semibold tracking-[-0.035em]', figure)}>{to}</span>
      {saving && <SavingTag saving={saving} />}
    </div>
  )
}

export function SavingTag({ saving, className }: { saving: string; className?: string }) {
  return (
    <span
      className={cn(
        'tnum rounded-note bg-buy-wash text-buy inline-flex items-center px-2 py-1 text-[0.8125rem] font-semibold',
        className,
      )}
    >
      Save {saving}
    </span>
  )
}

/* The Worth arrow: a squared-off head, not a generic chevron. Repeated
   wherever the product moves a number from one value to another. */
function ArrowRight() {
  return (
    <svg
      width="22"
      height="12"
      viewBox="0 0 22 12"
      fill="none"
      aria-hidden
      className="shrink-0 self-center"
    >
      <path
        d="M0 6h19M14.5 1.5 19.5 6l-5 4.5"
        stroke="var(--color-violet)"
        strokeWidth="1.75"
        strokeLinecap="square"
      />
    </svg>
  )
}

function ArrowDown() {
  return (
    <svg
      width="12"
      height="20"
      viewBox="0 0 12 20"
      fill="none"
      aria-hidden
      className="shrink-0 self-center"
    >
      <path
        d="M6 0v17M1.5 12.5 6 17.5l4.5-5"
        stroke="var(--color-violet)"
        strokeWidth="1.75"
        strokeLinecap="square"
      />
    </svg>
  )
}
