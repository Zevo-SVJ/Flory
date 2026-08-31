import { SiteNav } from '@/components/marketing/site-nav'
import { Hero } from '@/components/marketing/hero'
import { Hesitation } from '@/components/marketing/hesitation'
import { Categories } from '@/components/marketing/categories'
import { EvidenceWall } from '@/components/marketing/evidence-wall'
import { VerdictMoment } from '@/components/marketing/verdict-moment'
import { MoneyMoment } from '@/components/marketing/money-moment'
import { ShareMoment } from '@/components/marketing/share-moment'
import { PricingSection } from '@/components/marketing/pricing-section'
import { FinalCta } from '@/components/marketing/final-cta'
import { StickyAnalyzeBar } from '@/components/marketing/sticky-analyze-bar'

/**
 * The Worth landing page.
 *
 * One purchase, followed from doubt to decision: you found something (01), it
 * could be anything (02), Worth checks it (03), here's the answer (04), here's
 * what it saves you (05), and here's what you post about it (06). Every
 * section shows the same €399 headphones, so the page reads as one
 * investigation rather than a stack of unrelated feature demos.
 *
 * Fully static — no session lookup, no database call — so it's fast on a phone
 * over a mobile network. The only client JavaScript is the field, the hero
 * analysis, the price count-down and the sticky mobile bar.
 */
export default function LandingPage() {
  return (
    <>
      {/* On this page the nav button targets the hero field rather than a
          separate destination, so there is exactly one action above the fold. */}
      <SiteNav analyzeHref="/#analyze" />
      <Hero />
      <Hesitation />
      <Categories />
      <div id="how-it-works" className="scroll-mt-16">
        <EvidenceWall />
      </div>
      <VerdictMoment />
      <MoneyMoment />
      <ShareMoment />
      <PricingSection />
      <FinalCta />
      <StickyAnalyzeBar />
    </>
  )
}
