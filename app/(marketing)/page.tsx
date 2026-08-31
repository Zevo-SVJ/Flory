import { SiteNav } from '@/components/marketing/site-nav'
import { Hero } from '@/components/marketing/hero'
import { Problem } from '@/components/marketing/problem'
import { HowItWorks } from '@/components/marketing/how-it-works'
import { Dimensions } from '@/components/marketing/dimensions'
import { VerdictSection } from '@/components/marketing/verdict-section'
import { Money } from '@/components/marketing/money'
import { ShareSection } from '@/components/marketing/share-section'
import { Differentiation } from '@/components/marketing/differentiation'
import { PricingSection } from '@/components/marketing/pricing-section'
import { FinalCta } from '@/components/marketing/final-cta'
import { StickyAnalyzeBar } from '@/components/marketing/sticky-analyze-bar'

/**
 * The Worth landing page.
 *
 * Fully static — no session lookup, no database call — so it is fast on a phone
 * over a mobile network. Everything except three small islands of interactivity
 * (the input, the score count-up, the scroll reveals) is server-rendered.
 */
export default function LandingPage() {
  return (
    <>
      {/* On this page the nav button targets the hero input rather than a
          separate destination, so there is exactly one action above the fold. */}
      <SiteNav analyzeHref="/#analyze" />
      <Hero />
      <Problem />
      <HowItWorks />
      <Dimensions />
      <VerdictSection />
      <Money />
      <ShareSection />
      <Differentiation />
      <PricingSection />
      <FinalCta />
      <StickyAnalyzeBar />
    </>
  )
}
