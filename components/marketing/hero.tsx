import { AnalyzeInput } from '@/components/worth/analyze-input'
import { InvestigationScene } from '@/components/worth/investigation-scene'

/**
 * The hero.
 *
 * Question, then instrument, then answer — in that order and at that scale.
 * The headline reveals first, the field follows, and the scene beneath runs
 * the whole product in about three seconds: a checkout at its advertised
 * price, Worth reading it, the fees appearing, the six dimensions resolving,
 * the score, and the verdict last.
 *
 * The entire hero is one dark environment running from the top of the page,
 * so the navigation, the question, the field and the decision all belong to
 * the same world. It ends on a hard edge, not a fade.
 */
export function Hero() {
  return (
    <section className="scene scene-out relative overflow-hidden pt-20 pb-20 sm:pt-24 sm:pb-24">
      <div className="relative z-[1] mx-auto max-w-5xl px-5 text-center sm:px-6">
        <h1 className="text-hero motion-safe:anim-wipe mx-auto max-w-[15ch] font-serif font-medium text-white">
          Is it actually <span className="text-violet-lift">worth</span> it?
        </h1>

        <p
          className="text-lead motion-safe:anim-land mx-auto mt-6 max-w-[40ch] text-white/60"
          style={{ animationDelay: '160ms' }}
        >
          Paste a link. Worth does the research you were about to do yourself, and gives you a
          verdict before you spend.
        </p>

        <div
          id="analyze"
          className="motion-safe:anim-land mx-auto mt-9 max-w-[34rem] scroll-mt-24 sm:mt-10"
          style={{ animationDelay: '280ms' }}
        >
          <AnalyzeInput tone="dark" />
        </div>
      </div>

      <div className="relative z-[1] mt-14 px-5 sm:mt-20 sm:px-6">
        <InvestigationScene />
      </div>
    </section>
  )
}
