import Link from 'next/link'
import { cn } from '@/lib/utils/cn'
import { Wordmark } from './wordmark'

/**
 * Minimal marketing navigation.
 *
 * Stateless, so the landing page stays fully static. It never needs to know
 * whether you're signed in: /login redirects a signed-in visitor to the
 * dashboard, and /analyze routes signed-out visitors through sign-up.
 */
export function SiteNav({ analyzeHref = '/analyze' }: { analyzeHref?: string }) {
  return (
    <header className="pt-safe border-line/70 bg-ivory/80 sticky top-0 z-40 border-b backdrop-blur-md">
      <nav
        aria-label="Main"
        className="mx-auto flex h-15 max-w-6xl items-center justify-between gap-3 px-4 sm:h-16 sm:px-6"
      >
        <Link href="/" className="flex min-h-11 items-center rounded-sm" aria-label="Worth — home">
          <Wordmark />
        </Link>

        <div className="flex items-center gap-0.5 sm:gap-1">
          <NavLink href="/#how-it-works" desktopOnly>
            How it works
          </NavLink>
          <NavLink href="/pricing" desktopOnly>
            Pricing
          </NavLink>
          <NavLink href="/login">Sign in</NavLink>
          <Link
            href={analyzeHref}
            className={cn(
              'bg-worth ml-1.5 inline-flex h-11 items-center justify-center rounded-[0.5rem] px-4',
              'hover:bg-worth-deep text-[0.9375rem] font-medium text-white transition-colors',
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

function NavLink({
  href,
  children,
  desktopOnly,
}: {
  href: string
  children: React.ReactNode
  desktopOnly?: boolean
}) {
  return (
    <Link
      href={href}
      className={cn(
        'text-graphite min-h-11 items-center rounded-sm px-3 text-[0.9375rem] transition-colors',
        'hover:text-ink motion-reduce:transition-none',
        desktopOnly ? 'hidden sm:inline-flex' : 'inline-flex',
      )}
    >
      {children}
    </Link>
  )
}
