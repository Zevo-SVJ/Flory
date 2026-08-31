import { Section, Eyebrow, Statement } from './section'
import { cn } from '@/lib/utils/cn'

/**
 * Beat 01 — how it works.
 *
 * Three words and three visual cues, not three cards with icons in them:
 * PASTE, INVESTIGATE, DECIDE. Each step shows the actual thing that happens at
 * that moment — a field with a link in it, six dimensions being read, a score
 * with a verdict — so the process is visible rather than described.
 *
 * The connective rule between the steps is the only decoration, and it exists
 * to say "this is one movement, not three features".
 */
export function HowItWorks() {
  return (
    <Section id="how-it-works" width="wide">
      <div className="max-w-[34rem]">
        <Eyebrow index="01">How it works</Eyebrow>
        <Statement className="mt-5 max-w-[17ch]">Paste. Worth investigates. You decide.</Statement>
      </div>

      <ol className="mt-14 grid grid-cols-1 gap-12 sm:mt-20 lg:grid-cols-3 lg:gap-10">
        <Step index="01" name="Paste" caption="A link, a checkout, or a screenshot of one.">
          <div className="border-line-strong bg-surface flex h-14 items-center gap-2 rounded-full border px-4">
            <span aria-hidden className="text-faint text-[0.9375rem]">
              🔗
            </span>
            <span className="text-ink truncate text-[0.9375rem]">example.com/checkout</span>
            <span className="bg-violet ml-auto shrink-0 rounded-full px-4 py-2 text-[0.8125rem] font-semibold text-white">
              Analyze
            </span>
          </div>
        </Step>

        <Step
          index="02"
          name="Investigate"
          caption="Six dimensions, read in one pass instead of fifteen tabs."
        >
          <ul className="grid grid-cols-2 gap-x-6 gap-y-2.5">
            {['Price', 'Fees', 'Reviews', 'Trust', 'Risk', 'Alternatives'].map((d, i) => (
              <li key={d} className="flex items-center gap-2 text-[0.9375rem]">
                <span
                  aria-hidden
                  className={cn(
                    'size-1.5 shrink-0 rounded-full',
                    i === 1 ? 'bg-skip' : i === 4 ? 'bg-think' : 'bg-buy',
                  )}
                />
                <span className="text-ink-soft">{d}</span>
              </li>
            ))}
          </ul>
        </Step>

        <Step index="03" name="Decide" caption="One number, one call, and what it actually costs.">
          <div className="flex items-baseline gap-4">
            <span className="tnum text-think text-[3.25rem] leading-none font-semibold tracking-[-0.05em]">
              68
            </span>
            <span className="flex flex-col">
              <span className="text-think text-[1.125rem] leading-tight font-semibold">
                Think twice
              </span>
              <span className="tnum text-faint text-[0.8125rem]">out of 100</span>
            </span>
          </div>
        </Step>
      </ol>
    </Section>
  )
}

function Step({
  index,
  name,
  caption,
  children,
}: {
  index: string
  name: string
  caption: string
  children: React.ReactNode
}) {
  return (
    <li className="border-line border-t pt-6">
      <div className="flex items-baseline gap-3">
        <span className="tnum label text-violet">{index}</span>
        <h3 className="text-page text-ink font-medium">{name}</h3>
      </div>
      <p className="text-graphite mt-3 max-w-[32ch] text-[0.9375rem]">{caption}</p>
      <div className="mt-8">{children}</div>
    </li>
  )
}
