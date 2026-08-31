import Link from 'next/link'
import type { ReactNode } from 'react'
import { Wordmark } from '@/components/marketing/wordmark'
import { displayUrl } from '@/lib/analysis/format'

/**
 * Auth page shell.
 *
 * When a visitor arrived by pasting something, that link is shown back to them
 * here — proof the promise is being kept, and a reminder of why they're
 * creating an account.
 */
export function AuthShell({
  title,
  subtitle,
  pendingUrl,
  children,
  footer,
}: {
  title: string
  subtitle?: string
  pendingUrl?: string | null
  children: ReactNode
  footer?: ReactNode
}) {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="pt-safe px-4 py-5 sm:px-6">
        <Link href="/" className="rounded-note inline-flex" aria-label="Worth — home">
          <Wordmark />
        </Link>
      </header>

      <main className="flex flex-1 items-start justify-center px-4 pt-4 pb-16 sm:items-center sm:px-6 sm:pb-24">
        <div className="w-full max-w-[25rem]">
          <h1 className="text-heading text-ink font-serif font-medium">{title}</h1>
          {subtitle && (
            <p className="text-graphite mt-2 text-[0.9375rem] leading-snug">{subtitle}</p>
          )}

          {pendingUrl && (
            <div className="rounded-input border-line bg-ivory-deep mt-5 flex items-center gap-2.5 border px-3.5 py-3">
              <span className="bg-buy size-1.5 shrink-0 rounded-full" aria-hidden />
              <div className="min-w-0">
                <p className="text-graphite text-[0.6875rem] font-medium tracking-[0.1em] uppercase">
                  Waiting to be analysed
                </p>
                <p className="text-ink truncate text-[0.8125rem]" title={pendingUrl}>
                  {displayUrl(pendingUrl, 60)}
                </p>
              </div>
            </div>
          )}

          <div className="mt-7">{children}</div>

          {footer && <div className="text-graphite mt-6 text-[0.875rem]">{footer}</div>}
        </div>
      </main>
    </div>
  )
}

export function AuthDivider() {
  return (
    <div className="flex items-center gap-3" role="separator">
      <span className="bg-line h-px flex-1" />
      <span className="text-faint text-[0.75rem] tracking-[0.1em] uppercase">or</span>
      <span className="bg-line h-px flex-1" />
    </div>
  )
}
