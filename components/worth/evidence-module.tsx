import type { ReactNode } from 'react'
import { cn } from '@/lib/utils/cn'

/**
 * An evidence module.
 *
 * A discrete piece of information Worth gathered during the investigation:
 * flat, squared, hairline-bordered, with its dimension named in the corner —
 * closer to a filed note than a UI card. Deliberately not rounded and not
 * shadowed, so a wall of these reads as collected findings rather than a
 * feature grid.
 */
export function EvidenceModule({
  label,
  count,
  children,
  tone = 'neutral',
  className,
}: {
  label: string
  /** What Worth looked at to produce this, e.g. "11 retailers". */
  count?: string
  children: ReactNode
  tone?: 'neutral' | 'positive' | 'caution' | 'negative' | 'brand'
  className?: string
}) {
  return (
    <div
      className={cn(
        'border-line bg-surface flex flex-col gap-3 border p-4 sm:p-5',
        'rounded-note',
        tone === 'brand' && 'border-worth-line bg-worth-wash',
        tone === 'positive' && 'border-buy/20',
        tone === 'caution' && 'border-think/25',
        tone === 'negative' && 'border-skip/25',
        className,
      )}
    >
      <div className="flex items-baseline justify-between gap-3">
        <span className={cn('label', tone === 'brand' ? 'text-worth-deep' : 'text-graphite')}>
          {label}
        </span>
        {count && <span className="tnum text-faint text-[0.6875rem]">{count}</span>}
      </div>
      <div className="min-w-0">{children}</div>
    </div>
  )
}

/** A ticked finding. The marker is a filled square, not a generic checkmark. */
export function Finding({
  children,
  tone = 'positive',
}: {
  children: ReactNode
  tone?: 'positive' | 'caution' | 'negative'
}) {
  return (
    <li className="text-ink-soft flex items-start gap-2.5 text-[0.875rem] leading-snug">
      <span
        className={cn(
          'mt-[3px] flex size-3.5 shrink-0 items-center justify-center rounded-[2px]',
          tone === 'positive' && 'bg-buy/12 text-buy',
          tone === 'caution' && 'bg-think/12 text-think',
          tone === 'negative' && 'bg-skip/12 text-skip',
        )}
        aria-hidden
      >
        <svg width="9" height="9" viewBox="0 0 10 10" fill="none">
          {tone === 'positive' ? (
            <path
              d="m1.6 5.2 2.2 2.2L8.4 2.8"
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinecap="square"
            />
          ) : (
            <path
              d="M5 2v4M5 7.6v.6"
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinecap="square"
            />
          )}
        </svg>
      </span>
      <span>{children}</span>
    </li>
  )
}
