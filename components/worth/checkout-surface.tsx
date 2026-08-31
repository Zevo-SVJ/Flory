import { cn } from '@/lib/utils/cn'

/**
 * The thing Worth is looking at: a checkout.
 *
 * Not a photograph of an object, and not a fake browser window around one —
 * the decision Worth is about is the moment before you press pay, so the
 * subject of the page is the payment surface itself. It is drawn rather than
 * screenshotted, which is the honest option: no real company's checkout is
 * being reproduced, and no real price is being quoted.
 *
 * It renders in two registers so the same object can appear in Worth's light
 * sections and inside a dark scene without being redrawn.
 *
 * Every figure is illustrative. The surfaces that use this component carry the
 * disclosure.
 */

export interface CheckoutLine {
  label: string
  amount: string
  /** A line the buyer would not have seen until this screen. */
  late?: boolean
}

export function CheckoutSurface({
  title = 'Annual plan, paid upfront',
  meta = 'Order summary',
  lines,
  total,
  tone = 'light',
  /** Reveals the late-added lines. Used by the hero's investigation. */
  showLate = true,
  className,
}: {
  title?: string
  meta?: string
  lines: CheckoutLine[]
  total: string
  tone?: 'light' | 'dark'
  showLate?: boolean
  className?: string
}) {
  const dark = tone === 'dark'

  return (
    <div
      className={cn(
        'rounded-object w-full overflow-hidden border',
        dark ? 'border-white/12 bg-[#12101f]' : 'border-line bg-surface shadow-object',
        className,
      )}
    >
      <div className={cn('px-5 py-4 sm:px-6', dark ? 'bg-white/[0.03]' : 'bg-paper-2')}>
        <p className={cn('label', dark ? 'text-white/40' : 'text-faint')}>{meta}</p>
        <p
          className={cn(
            'mt-2 text-[1.0625rem] leading-snug font-medium',
            dark ? 'text-white' : 'text-ink',
          )}
        >
          {title}
        </p>
      </div>

      <dl className="px-5 py-4 sm:px-6">
        {lines.map((line) => (
          <div
            key={line.label}
            className={cn(
              'flex items-baseline justify-between gap-4 py-2.5',
              line.late && 'transition-opacity duration-500 motion-reduce:transition-none',
              line.late && !showLate && 'opacity-0',
            )}
          >
            <dt
              className={cn(
                'text-[0.9375rem]',
                line.late
                  ? dark
                    ? 'text-skip-lift'
                    : 'text-skip'
                  : dark
                    ? 'text-white/55'
                    : 'text-graphite',
              )}
            >
              {line.label}
            </dt>
            <dd
              className={cn(
                'tnum text-[0.9375rem] font-medium',
                line.late
                  ? dark
                    ? 'text-skip-lift'
                    : 'text-skip'
                  : dark
                    ? 'text-white/80'
                    : 'text-ink',
              )}
            >
              {line.amount}
            </dd>
          </div>
        ))}
      </dl>

      <div
        className={cn(
          'flex items-baseline justify-between gap-4 border-t px-5 py-4 sm:px-6',
          dark ? 'border-white/10' : 'border-line',
        )}
      >
        <span className={cn('label', dark ? 'text-white/40' : 'text-faint')}>Total today</span>
        <span
          className={cn(
            'tnum text-[1.5rem] leading-none font-semibold tracking-[-0.03em]',
            dark ? 'text-white' : 'text-ink',
          )}
        >
          {total}
        </span>
      </div>

      <div className={cn('px-5 pb-5 sm:px-6', dark ? '' : '')}>
        <div
          className={cn(
            'flex h-12 items-center justify-center rounded-full text-[0.9375rem] font-semibold',
            dark ? 'bg-white/90 text-[#12101f]' : 'bg-ink text-white',
          )}
        >
          Pay now
        </div>
      </div>
    </div>
  )
}
