import Link from 'next/link'
import { Wordmark } from './wordmark'

export function SiteFooter() {
  return (
    <footer className="border-rule bg-paper-sunk border-t">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6 sm:py-12">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <Wordmark />
          <nav aria-label="Footer" className="flex flex-wrap items-center gap-1">
            <Link
              href="/#how-it-works"
              className="rounded-chip text-muted hover:text-ink inline-flex min-h-11 items-center px-3 text-[0.875rem] transition motion-reduce:transition-none"
            >
              How it works
            </Link>
            <Link
              href="/pricing"
              className="rounded-chip text-muted hover:text-ink inline-flex min-h-11 items-center px-3 text-[0.875rem] transition motion-reduce:transition-none"
            >
              Pricing
            </Link>
            <Link
              href="/login"
              className="rounded-chip text-muted hover:text-ink inline-flex min-h-11 items-center px-3 text-[0.875rem] transition motion-reduce:transition-none"
            >
              Sign in
            </Link>
          </nav>
        </div>
        <p className="text-muted max-w-2xl text-[0.8125rem] leading-relaxed">
          Every result shown on this page is an illustrative example. Worth’s research engine isn’t
          connected yet, so no figure here describes a real product, price or analysis.
        </p>
      </div>
    </footer>
  )
}
