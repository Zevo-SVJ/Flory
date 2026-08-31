import type { ComponentProps, ReactNode } from 'react'
import { cn } from '@/lib/utils/cn'

/** A labelled form control. The label is always real, never a placeholder. */
export function Field({
  label,
  htmlFor,
  hint,
  error,
  children,
}: {
  label: string
  htmlFor: string
  hint?: ReactNode
  error?: string
  children: ReactNode
}) {
  const describedBy = error ? `${htmlFor}-error` : hint ? `${htmlFor}-hint` : undefined
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={htmlFor} className="text-ink text-sm font-medium">
        {label}
      </label>
      {children}
      {hint && !error && (
        <p id={describedBy} className="text-muted text-[0.8125rem]">
          {hint}
        </p>
      )}
      {error && (
        <p id={describedBy} className="text-skip text-[0.8125rem] font-medium">
          {error}
        </p>
      )}
    </div>
  )
}

export function Input({ className, ...props }: ComponentProps<'input'>) {
  return (
    <input
      className={cn(
        'rounded-input border-rule-strong bg-surface text-ink min-h-12 w-full border px-3.5',
        'placeholder:text-faint',
        'focus:border-ink focus:ring-ink/12 transition focus:ring-2 focus:outline-none',
        'motion-reduce:transition-none',
        className,
      )}
      {...props}
    />
  )
}
