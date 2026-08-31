import Link from 'next/link'
import { Wordmark } from './wordmark'

export function SiteFooter() {
  return (
    <footer className="border-line border-t">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6 sm:py-12">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <Wordmark />
          <nav aria-label="Footer" className="flex flex-wrap items-center gap-0.5">
            {[
              ['How it works', '/#how-it-works'],
              ['Pricing', '/pricing'],
              ['Sign in', '/login'],
            ].map(([label, href]) => (
              <Link
                key={href}
                href={href as string}
                className="text-graphite hover:text-ink inline-flex min-h-11 items-center rounded-sm px-3 text-[0.875rem] transition-colors motion-reduce:transition-none"
              >
                {label}
              </Link>
            ))}
          </nav>
        </div>
        <p className="text-graphite max-w-[62ch] text-[0.8125rem] leading-relaxed">
          Every result on this page is an illustrative example. Worth’s research engine isn’t
          connected yet, so no figure here describes a real product, price or analysis.
        </p>
      </div>
    </footer>
  )
}
