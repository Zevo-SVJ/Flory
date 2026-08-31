import { cn } from '@/lib/utils/cn'

/**
 * The Worth wordmark: editorial serif with a violet full stop. Small enough to
 * be quiet, specific enough to be ours — it repeats in the nav, the app shell,
 * the auth pages and the share card.
 */
export function Wordmark({
  className,
  tone = 'ink',
}: {
  className?: string
  tone?: 'ink' | 'light' | 'dark'
}) {
  return (
    <span
      className={cn(
        'font-serif text-[1.4375rem] leading-none font-medium tracking-[-0.02em] sm:text-[1.5rem]',
        tone === 'ink' ? 'text-ink' : 'text-white',
        className,
      )}
    >
      Worth<span className={tone === 'ink' ? 'text-violet' : 'text-violet-lift'}>.</span>
    </span>
  )
}
