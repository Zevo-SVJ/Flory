import { AnalyzeInput } from '@/components/worth/analyze-input'

/** Back to the one action. No newsletter, no second CTA. */
export function FinalCta() {
  return (
    <section className="border-rule border-t">
      <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 sm:py-28">
        <div className="mx-auto flex max-w-[42rem] flex-col items-center text-center">
          <h2 className="text-title text-ink font-serif font-medium">
            Thinking about buying something?
          </h2>
          <div className="mt-7 w-full sm:mt-8">
            <AnalyzeInput />
          </div>
        </div>
      </div>
    </section>
  )
}
