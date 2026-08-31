import { AnalyzeInput } from '@/components/worth/analyze-input'
import { ProductAnalysis } from '@/components/worth/product-analysis'

/**
 * The hero.
 *
 * Light stage, with the dark analysis object sitting on it — the two
 * environments meet in the first viewport, which sets up the rhythm the rest
 * of the page uses.
 *
 * "worth" carries the violet. One word, in the one place the brand name
 * appears at display size: enough to fix the colour to the name without
 * turning the headline into decoration.
 */
export function Hero() {
  return (
    <section className="relative overflow-hidden">
      {/* A soft violet field behind the top of the page, fading out rather than
          forming a coloured band. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 -top-40 h-[38rem] bg-[radial-gradient(55%_50%_at_50%_50%,rgba(91,61,245,0.16)_0%,transparent_70%)]"
      />

      <div className="relative mx-auto max-w-6xl px-5 pt-12 pb-16 sm:px-6 sm:pt-16 sm:pb-20 lg:pt-20 lg:pb-28">
        <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.02fr)] lg:gap-16">
          <div className="flex flex-col">
            <h1 className="text-hero text-ink font-serif font-medium">
              Is it actually <span className="text-violet">worth</span> it?
            </h1>

            <p className="text-lead text-graphite mt-6 max-w-[34ch]">
              Paste anything you’re thinking about buying. Worth checks the price, reviews, risks
              and alternatives — then gives you a clear verdict.
            </p>

            <div id="analyze" className="mt-8 scroll-mt-28 sm:mt-10">
              <AnalyzeInput />
            </div>

            {/* The breadth of input Worth takes — also the answer to "is this
                just an Amazon tool?". Desktop only: it balances the column
                against the analysis stage, but on a phone it would push the
                product proof below the fold, and the purchase-types section
                makes this argument properly further down. */}
            <div className="border-line mt-10 hidden items-center gap-x-2 gap-y-2 border-t pt-7 lg:flex lg:flex-wrap">
              <span className="label text-graphite mr-1">Works with</span>
              {['Product pages', 'Marketplaces', 'Software', 'Courses', 'Subscriptions'].map(
                (item) => (
                  <span
                    key={item}
                    className="border-line bg-surface/60 text-ink-soft rounded-full border px-3 py-1.5 text-[0.8125rem]"
                  >
                    {item}
                  </span>
                ),
              )}
            </div>
          </div>

          <div className="lg:pl-4">
            <ProductAnalysis />
          </div>
        </div>
      </div>
    </section>
  )
}
