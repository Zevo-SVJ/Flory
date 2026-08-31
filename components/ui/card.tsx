import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils/cn'

export function Card({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      className={cn('rounded-object border-line bg-surface shadow-object border', className)}
      {...props}
    />
  )
}

/** Small uppercase label. Used for data labels, never as decoration. */
export function Eyebrow({ className, ...props }: ComponentProps<'span'>) {
  return (
    <span
      className={cn(
        'text-graphite text-[0.6875rem] font-medium tracking-[0.12em] uppercase',
        className,
      )}
      {...props}
    />
  )
}
