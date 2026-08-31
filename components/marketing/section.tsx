import type { ReactNode } from 'react'
import { cn } from '@/lib/utils/cn'

export function Section({
  id,
  children,
  className,
  bleed = false,
}: {
  id?: string
  children: ReactNode
  className?: string
  bleed?: boolean
}) {
  return (
    <section
      id={id}
      className={cn('border-rule border-t', bleed ? 'bg-paper-sunk' : '', className)}
    >
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24">{children}</div>
    </section>
  )
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <p className="text-muted text-[0.6875rem] font-medium tracking-[0.16em] uppercase">
      {children}
    </p>
  )
}

export function SectionTitle({ children, className }: { children: ReactNode; className?: string }) {
  return <h2 className={cn('text-title text-ink font-serif font-medium', className)}>{children}</h2>
}
