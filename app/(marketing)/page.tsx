import { SiteNav } from '@/components/marketing/site-nav'
import { Hero } from '@/components/marketing/hero'
import { FoundSomething } from '@/components/marketing/found-something'
import { ShouldYouBuy } from '@/components/marketing/should-you-buy'
import { WorthChecks } from '@/components/marketing/worth-checks'
import { PurchaseTypes } from '@/components/marketing/purchase-types'
import { VerdictMoment } from '@/components/marketing/verdict-moment'
import { MoneyMoment } from '@/components/marketing/money-moment'
import { ProductDemo } from '@/components/marketing/product-demo'
import { ShareMoment } from '@/components/marketing/share-moment'
import { WhyWorth } from '@/components/marketing/why-worth'
import { PreLaunch } from '@/components/marketing/pre-launch'
import { PricingSection } from '@/components/marketing/pricing-section'
import { Faq } from '@/components/marketing/faq'
import { FinalCta } from '@/components/marketing/final-cta'
import { StickyAnalyzeBar } from '@/components/marketing/sticky-analyze-bar'

/**
 * The Worth landing page.
 *
 * One purchase followed from doubt to decision. The same €399 headphones run
 * through every section, so the page reads as a single investigation rather
 * than a stack of unrelated feature demos.
 *
 * The stage alternates between light (the consumer register — the thing you're
 * considering) and dark with violet lighting (Worth working — analysis,
 * evidence, verdict, the shared result). The switch happens when the content
 * changes register, not on a fixed cadence.
 *
 * Fully static: no session lookup and no database call, so it's fast on a phone
 * over a mobile network. The only client JavaScript is the field, the hero
 * analysis, the price count-down and the sticky mobile bar.
 */
export default function LandingPage() {
  return (
    <>
      {/* The nav's Analyze targets the hero field rather than a separate
          destination, so there is exactly one action above the fold. */}
      <SiteNav analyzeHref="/#analyze" over="scene" />

      <Hero />
      <FoundSomething />
      <ShouldYouBuy />
      <WorthChecks />
      <PurchaseTypes />
      <VerdictMoment />
      <MoneyMoment />
      <ProductDemo />
      <ShareMoment />
      <WhyWorth />
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
