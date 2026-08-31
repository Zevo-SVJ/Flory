import { cn } from '@/lib/utils/cn'

/** The Worth wordmark. Never set in all caps. */
export function Wordmark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        'text-ink font-serif text-[1.375rem] font-medium tracking-[-0.02em] sm:text-[1.5rem]',
        className,
      )}
    >
      Worth
    </span>
  )
}
