import { cn } from '@/lib/utils/cn'

/**
 * The Worth wordmark: editorial serif with a Worth Blue full stop. The dot is
 * small enough to be quiet and specific enough to be ours — it repeats in the
 * app shell, the auth pages and the share card.
 *
 * Never set in all caps.
 */
export function Wordmark({
  className,
  tone = 'ink',
}: {
  className?: string
  tone?: 'ink' | 'light'
}) {
  return (
    <span
      className={cn(
        'font-serif text-[1.4375rem] leading-none font-medium tracking-[-0.02em] sm:text-[1.5rem]',
        tone === 'ink' ? 'text-ink' : 'text-white',
        className,
      )}
    >
      Worth<span className="text-worth">.</span>
    </span>
  )
}
