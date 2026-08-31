import { cn } from '@/lib/utils/cn'

/**
 * Honesty rule.
 *
 * Worth is not yet performing real research. Every result produced by the
 * development fixture engine, and every illustrative example on the marketing
 * pages, carries this notice. Fixture output must never be mistaken for real
 * analysis.
 */
export function FixtureNotice({
  variant = 'inline',
  className,
}: {
  variant?: 'inline' | 'badge'
  className?: string
}) {
  if (variant === 'badge') {
    return (
      <span
        className={cn(
          'rounded-chip border-rule-strong bg-paper-sunk inline-flex items-center gap-1.5 border',
          'text-muted px-2 py-1 text-[0.625rem] font-medium tracking-[0.1em] uppercase',
          className,
        )}
      >
        <span className="bg-faint size-1.5 rounded-full" aria-hidden />
        Example analysis
      </span>
    )
  }

  return (
    <p
      className={cn(
        'rounded-input border-rule-strong bg-paper-sunk text-muted border px-3.5 py-3 text-[0.8125rem] leading-relaxed',
        className,
      )}
    >
      <strong className="text-ink-2 font-semibold">Sample result, not real research.</strong>{' '}
      Worth’s research engine isn’t connected yet, so this analysis comes from development fixture
      data. The numbers, signals and evidence below are placeholders — don’t make a purchase
      decision from them.
    </p>
  )
}
