import type { ReactNode } from 'react'
import { SiteNav } from '@/components/marketing/site-nav'

/**
 * Shared shell for the short legal/contact pages.
 *
 * These are deliberately brief and honest rather than boilerplate: Worth is
 * pre-launch, so a full policy copied from a template would describe a company
 * and a product that don't exist yet.
 */
export function LegalPage({ title, children }: { title: string; children: ReactNode }) {
  return (
    <>
      <SiteNav />
      <main className="mx-auto max-w-3xl px-5 pt-16 pb-24 sm:px-6 sm:pt-24">
        <h1 className="text-statement text-ink font-serif font-medium">{title}</h1>
        <div className="text-lead text-graphite [&_a]:text-violet [&_strong]:text-ink mt-8 flex flex-col gap-5 leading-relaxed [&_a]:font-medium [&_a]:underline [&_a]:underline-offset-4 [&_strong]:font-semibold">
          {children}
        </div>
      </main>
    </>
  )
}
