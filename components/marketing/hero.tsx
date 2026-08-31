'use client'

import { AnalyzeInput } from '@/components/worth/analyze-input'
import { WorthConsole } from '@/components/worth/worth-console'
import { useScrollProgress } from '@/lib/hooks/use-scroll-progress'

/**
 * The hero.
 *
 * A stage, lit from above, with one object standing on it. The headline is the
 * largest type on the page and carries almost no words; the field is right
 * under it because pasting a link is the product; and the console below is
 * Worth actually doing the thing, assembling itself while you read the
 * headline.
 *
 * Three depths, moving at three rates as you scroll away: the light, the type,
 * the object. That is what stops it reading as a flat page with a screenshot
 * on it.
 */
export function Hero() {
  const ref = useScrollProgress<HTMLElement>()

  return (
    <section
      ref={ref}
      className="stage stage-lit stage-grid scene-out depth relative overflow-hidden pt-24 pb-24 sm:pt-28 sm:pb-32"
    >
      <div className="relative z-[1] mx-auto max-w-6xl px-5 sm:px-6">
        {/* The question, at the size of a question that costs money. */}
        {/* The brand's question, not the visitor's. The visitor's — "should I
            actually buy this?" — is the subject of the next scene, and running
            both here would spend the page's largest type twice on one idea. */}
        <h1 className="text-hero motion-safe:anim-wipe depth-slow max-w-[11ch] font-serif font-medium text-balance text-white">
          Is it <span className="text-electric">actually</span> worth it?
        </h1>

        <div className="mt-10 grid grid-cols-1 gap-8 lg:mt-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:items-end lg:gap-16">
          <p
            className="text-lead motion-safe:anim-land max-w-[36ch] text-white/55"
            style={{ animationDelay: '180ms' }}
          >
            Paste a link. Worth reads the price, the fees, the reviews, the seller and the
            alternatives — then tells you whether it’s worth the money.
          </p>

          <div
            id="analyze"
            className="motion-safe:anim-land w-full scroll-mt-24"
            style={{ animationDelay: '300ms' }}
          >
            <AnalyzeInput tone="dark" />
          </div>
        </div>
      </div>

      {/* The object. Sits lower and moves faster than the type above it. */}
      <div className="depth-fast relative z-[1] mx-auto mt-16 max-w-5xl px-5 sm:mt-20 sm:px-6">
        <WorthConsole />

        <p className="mt-8 text-[0.8125rem] text-white/35">
          Illustrative analysis. Worth’s research engine isn’t connected yet, so this checkout,
          these figures and this verdict are written, not researched.
        </p>
      </div>
    </section>
  )
}
