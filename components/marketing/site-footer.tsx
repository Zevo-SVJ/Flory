import Link from 'next/link'
import { Wordmark } from './wordmark'

const GROUPS: Array<[string, Array<[string, string]>]> = [
  [
    'Product',
    [
      ['How it works', '/#how-it-works'],
      ['Pricing', '/#pricing'],
    ],
  ],
  [
    'Account',
    [
      ['Sign in', '/login'],
      ['Create a profile', '/signup'],
    ],
  ],
  [
    'Legal',
    [
      ['Privacy', '/privacy'],
      ['Terms', '/terms'],
      ['Contact', '/contact'],
    ],
  ],
]

export function SiteFooter() {
  return (
    <footer className="border-line bg-paper border-t">
      <div className="mx-auto max-w-6xl px-5 py-14 sm:px-6 sm:py-16">
        <div className="grid grid-cols-2 gap-10 sm:grid-cols-4">
          <div className="col-span-2 sm:col-span-1">
            <Wordmark />
            <p className="text-graphite mt-4 max-w-[26ch] text-[0.875rem] leading-relaxed">
              Know whether it’s worth your money, before you spend it.
            </p>
          </div>

          {GROUPS.map(([title, links]) => (
            <nav key={title} aria-label={title}>
              <h2 className="label text-faint">{title}</h2>
              <ul className="mt-3 flex flex-col">
                {links.map(([label, href]) => (
                  <li key={href}>
                    <Link
                      href={href}
                      className="text-graphite hover:text-ink inline-flex min-h-11 items-center text-[0.9375rem] transition-colors motion-reduce:transition-none"
                    >
                      {label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>

        <p className="border-line text-graphite mt-12 max-w-[64ch] border-t pt-8 text-[0.8125rem] leading-relaxed">
          Every result shown on this site is an illustrative example. Worth’s research engine isn’t
          connected yet, so no figure here describes a real product, price, seller or analysis.
        </p>
      </div>
    </footer>
  )
}
