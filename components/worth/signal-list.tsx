import type { Signal } from '@/lib/analysis/types'
import { TONE_STYLE } from '@/lib/analysis/verdict'
import { cn } from '@/lib/utils/cn'

/** The findings behind a verdict. Tone colour carries the meaning. */
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
    <ul className={cn('flex flex-col', compact ? 'gap-2' : 'divide-line divide-y', className)}>
      {signals.map((signal) => (
        <li
          key={`${signal.kind}-${signal.label}`}
          className={cn('flex items-start gap-3', compact ? '' : 'py-2.5 first:pt-0 last:pb-0')}
        >
          <span
            className={cn('mt-[7px] size-1.5 shrink-0 rounded-full', TONE_STYLE[signal.tone].dot)}
            aria-hidden
          />
          <p className="text-graphite min-w-0 flex-1 text-[0.875rem] leading-snug">
            <span className="text-ink font-semibold">{signal.label}</span>{' '}
            <span className="text-line-strong">·</span> {signal.detail}
          </p>
        </li>
      ))}
    </ul>
  )
}
