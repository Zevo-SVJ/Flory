import Link from 'next/link'
import { cn } from '@/lib/utils/cn'
import { Wordmark } from './wordmark'

/**
 * Floating navigation.
 *
 * A rounded, inset bar rather than a full-width bordered strip: it reads as an
 * object sitting on the page rather than browser chrome, and it lets the hero's
 * violet stage lighting run underneath it.
 *
 * Stateless by design, so the landing page stays fully static: `/login`
 * redirects a signed-in visitor onward, and `/analyze` routes signed-out
 * visitors through sign-up. Both links do the right thing either way.
 */
export function SiteNav({ analyzeHref = '/analyze' }: { analyzeHref?: string }) {
  return (
    <div className="pt-safe sticky top-0 z-50 px-3 pt-3 sm:px-5 sm:pt-4">
      <header
        className={cn(
          'mx-auto flex max-w-6xl items-center justify-between gap-3 rounded-full',
          'border-line/80 bg-paper/80 border py-2 pr-2 pl-4 backdrop-blur-xl sm:pr-2.5 sm:pl-6',
          'shadow-[0_1px_2px_rgba(18,18,26,0.04),0_10px_30px_-18px_rgba(18,18,26,0.25)]',
        )}
      >
        <Link href="/" className="flex min-h-11 items-center" aria-label="Worth — home">
          <Wordmark />
        </Link>

        <nav aria-label="Main" className="flex items-center gap-0.5 sm:gap-1">
          <NavLink href="/#how-it-works" desktopOnly>
            How it works
          </NavLink>
          <NavLink href="/#pricing" desktopOnly>
            Pricing
          </NavLink>
          <NavLink href="/login">Sign in</NavLink>
          <Link
            href={analyzeHref}
            className={cn(
              'bg-violet ml-1 inline-flex h-11 items-center justify-center rounded-full px-5',
              'hover:bg-violet-deep text-[0.9375rem] font-medium text-white transition-colors',
              'motion-reduce:transition-none',
            )}
          >
            Analyze
          </Link>
        </nav>
      </header>
    </div>
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
        'text-graphite min-h-11 items-center rounded-full px-3.5 text-[0.9375rem]',
        'hover:text-ink transition-colors motion-reduce:transition-none',
        desktopOnly ? 'hidden sm:inline-flex' : 'inline-flex',
      )}
    >
      {children}
    </Link>
  )
}
