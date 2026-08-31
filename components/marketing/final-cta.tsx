import { AnalyzeInput } from '@/components/worth/analyze-input'

/**
 * Back to the one action. No newsletter, no second CTA, no upsell.
 *
 * The closing line is the differentiation argument compressed into two
 * sentences, so the page ends on what Worth is for rather than on a form.
 */
export function FinalCta() {
  return (
    <section className="border-line border-t">
      <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 sm:py-28">
        <div className="mx-auto flex max-w-[44rem] flex-col items-center text-center">
          <p className="text-heading text-faint max-w-[30ch] font-serif leading-snug font-normal">
            Most shopping tools help you find products.
          </p>
          <h2 className="text-statement text-ink mt-3 max-w-[22ch] font-serif font-medium">
            Worth tells you whether to buy the one you’ve already found.
          </h2>

          <div className="mt-9 w-full max-w-[38rem]">
            <AnalyzeInput />
          </div>
        </div>
      </div>
    </section>
  )
}
