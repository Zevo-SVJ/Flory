import type { ReactNode } from 'react'
import { cn } from '@/lib/utils/cn'

/**
 * Sections share one ivory ground and are separated by a hairline rather than
 * by alternating background blocks. The page should read as one continuous
 * surface that occasionally arrives somewhere important, not as a stack of
 * marketing panels.
 */
export function Section({
  id,
  children,
  className,
  rule = true,
  tone = 'ivory',
}: {
  id?: string
  children: ReactNode
  className?: string
  rule?: boolean
  tone?: 'ivory' | 'ink'
}) {
  return (
    <section
      id={id}
      className={cn(
        rule && tone === 'ivory' && 'border-line border-t',
        tone === 'ink' && 'bg-ink text-white',
        className,
      )}
    >
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24">{children}</div>
    </section>
  )
}

/**
 * The numbered story beat. Numbering is real here — the landing page follows
 * one purchase from doubt to decision — so the index carries information.
 */
export function Beat({ index, children }: { index: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline gap-3">
      <span className="tnum label text-worth">{index}</span>
      <span className="label text-graphite">{children}</span>
    </div>
  )
}

export function Statement({ children, className }: { children: ReactNode; className?: string }) {
  return <h2 className={cn('text-statement font-serif font-medium', className)}>{children}</h2>
}
