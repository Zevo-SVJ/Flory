import { SiteNav } from '@/components/marketing/site-nav'
import { Hero } from '@/components/marketing/hero'
import { HowItWorks } from '@/components/marketing/how-it-works'
import { WhyBother } from '@/components/marketing/why-bother'
import { VerdictMoment } from '@/components/marketing/verdict-moment'
import { PurchaseTypes } from '@/components/marketing/purchase-types'
import { ProductDemo } from '@/components/marketing/product-demo'
import { ShareMoment } from '@/components/marketing/share-moment'
import { PreLaunch } from '@/components/marketing/pre-launch'
import { PricingSection } from '@/components/marketing/pricing-section'
import { Faq } from '@/components/marketing/faq'
import { FinalCta } from '@/components/marketing/final-cta'
import { StickyAnalyzeBar } from '@/components/marketing/sticky-analyze-bar'

/**
 * The Worth landing page.
 *
 * One decision, followed from doubt to conclusion. The same checkout runs
 * through every section — advertised at €892, actually €1,007, available
 * elsewhere at €724 — so the page reads as a single investigation rather than
 * a stack of unrelated feature demos.
 *
 * The narrative, in order:
 *
 *   hero          I am about to pay for something.
 *   how it works  Paste it. Worth investigates. You decide.
 *   why bother    I would otherwise do this research myself:
 *                   01 the research      chaos becomes one answer
 *                   02 the real price    what actually leaves my account
 *                   03 the alternative   something better exists
 *   the answer    the six dimensions, and what they add up to
 *   anywhere      it works on more than one kind of spend
 *   using it      this is the product, on a phone
 *   it travels    the result is worth posting
 *   honesty       nothing here has launched yet
 *   pricing, questions, and the field again
 *
 * Colour worlds change on hard edges, never on a fade: dark is Worth working,
 * light is the visitor's own register. The switch happens when the content
 * changes register, not on a fixed cadence.
 *
 * Fully static: no session lookup and no database call, so it's fast on a
 * phone over a mobile network.
 */
export default function LandingPage() {
  return (
    <>
      {/* The nav's Analyze targets the hero field rather than a separate
          destination, so there is exactly one action above the fold. */}
      <SiteNav analyzeHref="/#analyze" over="scene" />

      <Hero />
      <HowItWorks />
      <WhyBother />
      <VerdictMoment />
      <PurchaseTypes />
      <ProductDemo />
      <ShareMoment />
      <PreLaunch />
      <PricingSection />
      <div id="faq" className="scroll-mt-24">
        <Faq />
      </div>
      <FinalCta />

      <StickyAnalyzeBar />
    </>
  )
}
