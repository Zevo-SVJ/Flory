import { AnalyzeInput } from '@/components/worth/analyze-input'
import { VerdictCard } from '@/components/worth/verdict-card'
import { HERO_EXAMPLE } from '@/lib/analysis/fixtures'

/**
 * The hero.
 *
 * The product interaction IS the hero: headline, one sentence, the input, and
 * a real Worth result directly beneath it. A visitor arriving from a short-form
 * video should understand what to do without reading anything else.
 *
 * Centred single column rather than a two-column split — a split hero forces a
 * compromise on mobile, and mobile is the primary target.
 */
export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="mx-auto max-w-6xl px-4 pt-12 pb-14 sm:px-6 sm:pt-20 sm:pb-20">
        <div className="mx-auto flex max-w-[46rem] flex-col items-center text-center">
          <h1 className="text-display text-ink font-serif font-medium">Is it actually worth it?</h1>

          <p className="text-lead text-muted mt-5 max-w-[34rem]">
            Paste what you’re thinking about buying. Worth investigates the price, reviews, risks
            and alternatives — then helps you decide.
          </p>

          <div id="analyze" className="mt-8 w-full max-w-[42rem] scroll-mt-24 sm:mt-10">
            <AnalyzeInput autoFocus={false} />
          </div>
        </div>

        {/* The product preview sits immediately beneath the action it explains. */}
        <div className="mx-auto mt-12 max-w-[40rem] sm:mt-16">
          <p className="text-muted mb-3 text-center text-[0.8125rem]">This is what comes back:</p>
          <VerdictCard analysis={HERO_EXAMPLE} />
        </div>
      </div>
    </section>
  )
}
