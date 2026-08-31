import { SiteNav } from '@/components/marketing/site-nav'
import { Hero } from '@/components/marketing/hero'
import { TheQuestion } from '@/components/marketing/the-question'
import { TheProcess } from '@/components/marketing/the-process'
import { VerdictMoment } from '@/components/marketing/verdict-moment'
import { ValueRisk } from '@/components/marketing/value-risk'
import { WhyBother } from '@/components/marketing/why-bother'
import { PreLaunch } from '@/components/marketing/pre-launch'
import { PricingSection } from '@/components/marketing/pricing-section'
import { FinalCta } from '@/components/marketing/final-cta'
import { StickyAnalyzeBar } from '@/components/marketing/sticky-analyze-bar'

/**
 * The Worth landing page.
 *
 * Seven scenes, not a stack of sections. Each one has a single dominant visual
 * idea and hands over to the next:
 *
 *   01  the object      Worth, standing on a lit stage, assembling itself
 *   02  the question    "should I actually buy this?", inside the noise
 *   03  the process     one pinned panel, transformed by the scroll
 *   04  the verdict     the score, surrounded by the evidence it came from
 *   05  value / risk    a beam settling off level — good is not worth it
 *   06  the money       what it really costs, and what Worth found instead
 *   07  the invitation  the field again, on the darkest screen of the page
 *
 * Between them sit the two things that have to be said plainly rather than
 * staged: that nothing has launched yet, and what it will cost.
 *
 * One example runs through all of it — a checkout advertised at €892 that is
 * €1,007 once fees are counted, and €724 elsewhere — so the page reads as one
 * investigation rather than seven demos. Every figure is illustrative and every
 * surface that shows one says so.
 *
 * Fully static: no session lookup and no database call. The only client
 * JavaScript is the field, the console's build sequence, and two scroll
 * listeners that write CSS custom properties without re-rendering.
 */
export default function LandingPage() {
  return (
    <>
      {/* Over the hero, not above it: the nav is fixed inside the first screen
          so the stage runs to the top of the viewport. */}
      <SiteNav analyzeHref="/#analyze" over="scene" floating />

      <Hero />
      <TheQuestion />
      <TheProcess />
      <VerdictMoment />
      <ValueRisk />
      <WhyBother />
      <PreLaunch />
      <PricingSection />
      <FinalCta />

      <StickyAnalyzeBar />
    </>
  )
}
