import { AnalyzeInput } from '@/components/worth/analyze-input'

/**
 * The close.
 *
 * Dark stage with violet lighting and the field sitting in the middle of it.
 * The product is the call to action — there's no "Get started", no newsletter
 * and no second button competing with it.
 */
export function FinalCta() {
  return (
    <section className="scene scene-in relative overflow-hidden">
      <div className="relative mx-auto max-w-6xl px-5 py-24 sm:px-6 sm:py-32">
        <div className="mx-auto flex max-w-[42rem] flex-col items-center text-center">
          <h2 className="text-statement font-serif font-medium text-white">
            Before you spend it, check it.
          </h2>
          <p className="text-lead mt-5 text-white/55">Paste the link. Get the verdict.</p>

          <div className="mt-10 w-full">
            <AnalyzeInput tone="dark" />
          </div>
        </div>
      </div>
    </section>
  )
}
