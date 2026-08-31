import type { Metadata } from 'next'
import { SiteNav } from '@/components/marketing/site-nav'
import { PricingSection } from '@/components/marketing/pricing-section'
import { AnalyzeInput } from '@/components/worth/analyze-input'

export const metadata: Metadata = {
  title: 'Pricing',
  description:
    'Worth will launch with three paid plans and no permanent free tier. Prices are not final yet.',
  alternates: { canonical: '/pricing' },
}

export default function PricingPage() {
  return (
    <>
      <SiteNav />
      <div className="mx-auto max-w-6xl px-4 pt-14 pb-4 sm:px-6 sm:pt-20">
        <h1 className="text-title text-ink font-serif font-medium">
          Three plans. All paid. None of them priced yet.
        </h1>
        <p className="text-lead text-muted mt-4 max-w-[52ch]">
          Worth is being built in the open and hasn’t launched. Rather than show a price we haven’t
          committed to, here is the shape of what’s coming.
        </p>
      </div>
      <PricingSection heading={false} />
      <section className="border-rule border-t">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
          <div className="mx-auto flex max-w-[42rem] flex-col items-center text-center">
            <h2 className="text-heading text-ink font-serif font-medium">
              In the meantime — is it actually worth it?
            </h2>
            <div className="mt-6 w-full">
              <AnalyzeInput size="md" />
            </div>
          </div>
        </div>
      </section>
    </>
  )
}
