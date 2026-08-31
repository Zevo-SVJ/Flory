import Link from 'next/link'
import { cn } from '@/lib/utils/cn'
import { Wordmark } from './wordmark'

/**
 * Minimal marketing navigation.
 *
 * Deliberately stateless, so the landing page stays fully static and fast on a
 * phone. It never needs to know whether you are signed in: `/login` redirects a
 * signed-in visitor to `/dashboard`, and `/analyze` routes signed-out visitors
 * through sign-up. Both links do the right thing either way.
 *
 * On the landing page `analyzeHref` is an anchor to the hero input, so the nav
 * button and the hero button are the same action rather than competing CTAs.
 */
export function SiteNav({ analyzeHref = '/analyze' }: { analyzeHref?: string }) {
  return (
    <header className="pt-safe border-rule/70 bg-paper/85 sticky top-0 z-40 border-b backdrop-blur-md">
      <nav
        aria-label="Main"
        className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-3 px-4 sm:h-16 sm:px-6"
      >
        <Link
          href="/"
          className="rounded-chip flex min-h-11 items-center"
          aria-label="Worth — home"
        >
          <Wordmark />
        </Link>

        <div className="flex items-center gap-1 sm:gap-2">
          <Link
            href="/#how-it-works"
            className="rounded-chip text-muted hover:text-ink hidden min-h-11 items-center px-3 text-[0.9375rem] transition motion-reduce:transition-none sm:inline-flex"
          >
            How it works
          </Link>
          <Link
            href="/pricing"
            className="rounded-chip text-muted hover:text-ink hidden min-h-11 items-center px-3 text-[0.9375rem] transition motion-reduce:transition-none sm:inline-flex"
          >
            Pricing
          </Link>
          <Link
            href="/login"
            className="rounded-chip text-muted hover:text-ink inline-flex min-h-11 items-center px-3 text-[0.9375rem] transition motion-reduce:transition-none"
          >
            Sign in
          </Link>
          <Link
            href={analyzeHref}
            className={cn(
              'rounded-input bg-ink inline-flex h-11 items-center justify-center px-4',
              'text-paper hover:bg-ink-2 text-[0.9375rem] font-medium transition',
              'motion-reduce:transition-none',
            )}
          >
            Analyze
          </Link>
        </div>
      </nav>
    </header>
  )
}
