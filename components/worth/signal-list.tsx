import type { Signal } from '@/lib/analysis/types'
import { TONE_STYLE } from '@/lib/analysis/verdict'
import { cn } from '@/lib/utils/cn'

/** The evidence signals behind a verdict. Tone is the only colour. */
export function SignalList({
  signals,
  compact = false,
  className,
}: {
  signals: Signal[]
  compact?: boolean
  className?: string
}) {
  if (signals.length === 0) return null

  return (
    <ul className={cn('flex flex-col', compact ? 'gap-2' : 'divide-rule divide-y', className)}>
      {signals.map((signal) => (
        <li
          key={`${signal.kind}-${signal.label}`}
          className={cn('flex items-start gap-2.5', compact ? '' : 'py-2.5 first:pt-0 last:pb-0')}
        >
          <span
            className={cn('mt-1.5 size-1.5 shrink-0 rounded-full', TONE_STYLE[signal.tone].dot)}
            aria-hidden
          />
          <div className="min-w-0 flex-1">
            <span className="text-ink text-[0.8125rem] font-semibold">{signal.label}</span>
            <span className="text-muted ml-2 text-[0.8125rem] leading-snug">{signal.detail}</span>
          </div>
        </li>
      ))}
    </ul>
  )
}
