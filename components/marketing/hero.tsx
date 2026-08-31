import { AnalyzeInput } from '@/components/worth/analyze-input'
import { LiveAnalysis } from '@/components/worth/live-analysis'

/**
 * The hero.
 *
 * Asymmetric two-column on desktop: the claim and the field on the left, the
 * investigation running on the right. On mobile the field stays directly under
 * the headline and the analysis follows immediately beneath it — the visitor
 * sees the action and the outcome in one screen.
 *
 * "worth" is set in Worth Blue. One word, in the one place the brand name
 * appears at display size — enough to fix the colour to the name without
 * turning the headline into decoration.
 */
export function Hero() {
  return (
    <section className="relative">
      {/* A single soft brand field behind the hero, fading into the ivory
          ground so the page begins as one surface rather than a coloured band. */}
      <div
        aria-hidden
        className="from-worth-wash/70 pointer-events-none absolute inset-x-0 top-0 h-[26rem] bg-gradient-to-b to-transparent"
      />

      <div className="relative mx-auto max-w-6xl px-4 pt-10 pb-12 sm:px-6 sm:pt-14 sm:pb-16 lg:pt-16 lg:pb-20">
        <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.92fr)] lg:gap-16">
          <div className="flex flex-col">
            <h1 className="text-hero text-ink font-serif font-medium">
              Is it actually <span className="text-worth">worth</span> it?
            </h1>

            <p className="text-lead text-graphite mt-5 max-w-[36ch]">
              Paste anything you’re thinking about buying. Worth checks the price, reviews, risks
              and alternatives — then gives you a clear verdict.
            </p>

            <div id="analyze" className="mt-7 scroll-mt-24 sm:mt-9">
              <AnalyzeInput />
            </div>

            {/* States the breadth of input Worth takes, which is also the
                answer to "is this just an Amazon tool?".

                Desktop only: it balances the column against the analysis
                panel there, but on a phone it would push the product proof
                below the fold, and the Categories section already makes this
                argument properly. */}
            <div className="border-line/80 mt-8 hidden flex-wrap items-center gap-x-2.5 gap-y-2 border-t pt-6 lg:flex">
              <span className="label text-graphite">Works with</span>
              {['Product pages', 'Marketplaces', 'Software', 'Courses', 'Subscriptions'].map(
                (item) => (
                  <span
                    key={item}
                    className="rounded-note border-line bg-surface/70 text-ink-soft border px-2.5 py-1 text-[0.8125rem]"
                  >
                    {item}
                  </span>
                ),
              )}
            </div>
          </div>

          <div className="lg:pl-2">
            <LiveAnalysis />
            <p className="text-faint mt-3 text-center text-[0.75rem] lg:text-left">
              Illustrative analysis — Worth’s research engine isn’t connected yet.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
