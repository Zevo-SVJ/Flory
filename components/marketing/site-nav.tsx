'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils/cn'
import { Wordmark } from './wordmark'

/**
 * Navigation.
 *
 * Over the hero it is not a bar at all — the wordmark and the links sit
 * directly on the dark scene, so the first screen is the product rather than a
 * product with a widget floating over it. Once the visitor leaves the hero the
 * bar materialises: a translucent dark strip that keeps Worth's environment
 * with them down a page that is mostly light.
 *
 * Stateless by design, so the landing page stays fully static: `/login`
 * redirects a signed-in visitor onward, and `/analyze` routes signed-out
 * visitors through sign-up. Both links do the right thing either way.
 */
export function SiteNav({
  analyzeHref = '/analyze',
  over = 'paper',
}: {
  analyzeHref?: string
  /** 'scene' sits on Worth's dark hero; 'paper' on the light pages. */
  over?: 'scene' | 'paper'
}) {
  const dark = over === 'scene'
  const [lifted, setLifted] = useState(false)

  useEffect(() => {
    const onScroll = () => setLifted(window.scrollY > 24)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <div
      className={cn(
        'pt-safe sticky top-0 z-50 border-b transition-colors duration-300',
        'motion-reduce:transition-none',
        dark
          ? /* Continuous with the hero scene at rest, then a blurred strip once
               the visitor has scrolled past it. */
            lifted
            ? 'border-white/10 bg-[#07060e]/85 backdrop-blur-xl'
            : 'border-transparent bg-[#07060e]'
          : lifted
            ? 'border-line/70 bg-paper/85 backdrop-blur-xl'
            : 'border-transparent bg-paper',
      )}
    >
      <header className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-2.5 sm:px-6 sm:py-3">
        <Link href="/" className="flex min-h-11 items-center" aria-label="Worth — home">
          <Wordmark tone={dark ? 'dark' : 'ink'} />
        </Link>

        <nav aria-label="Main" className="flex items-center gap-0.5 sm:gap-1">
          {/* Three things, at every width. A landing page with one action
              does not need a menu, and section links only compete with it. */}
          <NavLink href="/login" dark={dark}>
            Sign in
          </NavLink>
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
  dark,
  desktopOnly,
}: {
  href: string
  children: React.ReactNode
  dark?: boolean
  desktopOnly?: boolean
}) {
  return (
    <Link
      href={href}
      className={cn(
        'min-h-11 items-center rounded-full px-3.5 text-[0.9375rem] transition-colors',
        'motion-reduce:transition-none',
        dark ? 'text-white/60 hover:text-white' : 'text-graphite hover:text-ink',
        desktopOnly ? 'hidden sm:inline-flex' : 'inline-flex',
      )}
    >
      {children}
    </Link>
  )
}
