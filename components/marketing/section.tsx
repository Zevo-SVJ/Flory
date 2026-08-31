import type { ReactNode } from 'react'
import { cn } from '@/lib/utils/cn'

/**
 * A section is a stage.
 *
 * `light` is the consumer/editorial register — the thing you're considering.
 * `dark` is Worth working: analysis, evidence, verdict, the shared result.
 * The page changes stage when the content changes register, not on a fixed
 * alternating cadence.
 */
export function Section({
  id,
  children,
  tone = 'light',
  glow = false,
  className,
  width = 'default',
}: {
  id?: string
  children: ReactNode
  tone?: 'light' | 'dark' | 'sunk'
  /** Violet stage lighting. Dark sections only. */
  glow?: boolean
  className?: string
  width?: 'default' | 'wide'
}) {
  return (
    <section
      id={id}
      className={cn(
        'relative overflow-hidden',
        tone === 'light' && 'bg-paper text-ink',
        tone === 'sunk' && 'bg-paper-2 text-ink',
        tone === 'dark' && 'bg-midnight text-white',
        glow && tone === 'dark' && 'stage-light',
        className,
      )}
    >
      <div
        className={cn(
          'relative mx-auto px-5 py-20 sm:px-6 sm:py-28 lg:py-32',
          width === 'wide' ? 'max-w-7xl' : 'max-w-6xl',
        )}
      >
        {children}
      </div>
    </section>
  )
}

/**
 * The section eyebrow. Numbering is real — the page follows one purchase from
 * doubt to decision — so the index carries information.
 */
export function Eyebrow({
  index,
  children,
  tone = 'light',
}: {
  index?: string
  children: ReactNode
  tone?: 'light' | 'dark'
}) {
  return (
    <div className="flex items-baseline gap-3">
      {index && <span className="tnum label text-violet">{index}</span>}
      <span className={cn('label', tone === 'dark' ? 'text-white/45' : 'text-graphite')}>
        {children}
      </span>
    </div>
  )
}

export function Statement({
  children,
  tone = 'light',
  className,
}: {
  children: ReactNode
  tone?: 'light' | 'dark'
  className?: string
}) {
  return (
    <h2
      className={cn(
        'text-statement font-serif font-medium',
        tone === 'dark' ? 'text-white' : 'text-ink',
        className,
      )}
    >
      {children}
    </h2>
  )
}

/** The illustrative-data disclosure. Every example on the page carries one. */
export function Disclosure({
  children = 'Illustrative example — Worth’s research engine isn’t connected yet.',
  tone = 'light',
  className,
}: {
  children?: ReactNode
  tone?: 'light' | 'dark'
  className?: string
}) {
  return (
    <p
      className={cn('text-[0.75rem]', tone === 'dark' ? 'text-white/35' : 'text-faint', className)}
    >
      {children}
    </p>
  )
}
