import Link from 'next/link'
import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils/cn'

type Variant = 'primary' | 'secondary' | 'ghost'
type Size = 'md' | 'lg'

const base =
  'inline-flex items-center justify-center gap-2 rounded-[0.5rem] font-medium transition ' +
  'disabled:cursor-not-allowed disabled:opacity-50 active:scale-[0.985] ' +
  'motion-reduce:transition-none motion-reduce:active:scale-100'

/* Primary is ink, never a colour — colour is reserved for verdicts. */
const variants: Record<Variant, string> = {
  primary: 'bg-violet text-white hover:bg-violet-deep',
  secondary: 'border border-line-strong bg-surface text-ink hover:border-ink hover:bg-paper-2',
  ghost: 'text-graphite hover:bg-paper-2 hover:text-ink',
}

/* Every size clears the 44px minimum touch target. */
const sizes: Record<Size, string> = {
  md: 'min-h-11 px-4 text-[0.9375rem]',
  lg: 'min-h-13 px-6 text-base',
}

export function Button({
  variant = 'primary',
  size = 'md',
  className,
  ...props
}: ComponentProps<'button'> & { variant?: Variant; size?: Size }) {
  return <button className={cn(base, variants[variant], sizes[size], className)} {...props} />
}

export function ButtonLink({
  variant = 'primary',
  size = 'md',
  className,
  ...props
}: ComponentProps<typeof Link> & { variant?: Variant; size?: Size }) {
  return <Link className={cn(base, variants[variant], sizes[size], className)} {...props} />
}
