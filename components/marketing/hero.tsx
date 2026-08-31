import { AnalyzeInput } from '@/components/worth/analyze-input'
import { InvestigationScene } from '@/components/worth/investigation-scene'

/**
 * The hero.
 *
 * A product launch, not a SaaS masthead: one centred question, one field, and
 * then the product itself — full width, lit, being investigated. There is no
 * two-column "copy on the left, screenshot on the right" arrangement, because
 * that layout puts the product beside the argument rather than making it the
 * argument.
 *
 * The whole hero is one dark scene running from the top of the page, so the
 * navigation, the question, the field and the product all belong to the same
 * environment. It feathers out at the bottom into the light section beneath.
 */
export function Hero() {
  return (
    <section className="scene scene-out relative overflow-hidden pt-28 pb-24 sm:pt-32 sm:pb-28">
      <div className="relative z-[1] mx-auto max-w-6xl px-5 text-center sm:px-6">
        <h1 className="text-hero mx-auto max-w-[16ch] font-serif font-medium text-white">
          Is it actually <span className="text-violet-lift">worth</span> it?
        </h1>

        <p className="text-lead mx-auto mt-6 max-w-[38ch] text-white/60">
          Paste anything you’re about to buy. Worth checks the price, the reviews, the seller and
          the alternatives — then tells you straight.
        </p>

        <div id="analyze" className="mx-auto mt-9 max-w-[34rem] scroll-mt-28 sm:mt-10">
          <AnalyzeInput tone="dark" />
        </div>
      </div>

      {/* The product, at scale. */}
      <InvestigationScene className="relative z-[1] mt-14 sm:mt-16" />
    </section>
  )
}
