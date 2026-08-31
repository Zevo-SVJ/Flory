import { Section, SectionLabel, SectionTitle } from './section'
import { Reveal } from './reveal'
import { Card } from '@/components/ui/card'
import { ScoreDial } from '@/components/worth/score-dial'
import { SIGNAL_ORDER, SIGNAL_LABEL } from '@/lib/analysis/verdict'

/**
 * Three steps. The numbering is real — this is a sequence — and each step shows
 * an actual fragment of Worth's interface rather than an illustration.
 */
export function HowItWorks() {
  return (
    <Section id="how-it-works">
      <div className="flex flex-col gap-3">
        <SectionLabel>How it works</SectionLabel>
        <SectionTitle className="max-w-[20ch]">Three steps, about a minute.</SectionTitle>
      </div>

      <ol className="mt-10 grid grid-cols-1 gap-4 sm:mt-14 md:grid-cols-3 md:gap-5">
        <Step index="01" title="Paste it" body="Paste the product, offer or URL.">
          <div className="rounded-input border-rule-strong bg-surface flex h-11 items-center border px-3">
            <span className="text-faint truncate text-[0.8125rem]">
              Paste a product, offer or URL…
            </span>
          </div>
        </Step>

        <Step
          index="02"
          title="Worth investigates"
          body="It researches the things that actually matter."
        >
          <ul className="flex flex-col gap-1.5">
            {SIGNAL_ORDER.map((kind, index) => (
              <li key={kind} className="flex items-center gap-2.5">
                <span
                  className={
                    index < 4
                      ? 'bg-ink flex size-4 shrink-0 items-center justify-center rounded-full'
                      : 'border-rule-strong size-4 shrink-0 rounded-full border'
                  }
                  aria-hidden
                >
                  {index < 4 && (
                    <svg width="9" height="9" viewBox="0 0 10 10" fill="none">
                      <path
                        d="m1.8 5.2 2 2L8.2 2.8"
                        stroke="var(--color-paper)"
                        strokeWidth="1.6"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  )}
                </span>
                <span
                  className={
                    index < 4 ? 'text-ink text-[0.8125rem]' : 'text-faint text-[0.8125rem]'
                  }
                >
                  {SIGNAL_LABEL[kind]}
                </span>
              </li>
            ))}
          </ul>
        </Step>

        <Step
          index="03"
          title="Get your verdict"
          body="See the score, the evidence, the risks and better alternatives."
        >
          <div className="flex items-center gap-3">
            <ScoreDial score={34} verdict="skip" size="sm" />
            <div>
              <p className="text-skip text-xl leading-none font-semibold tracking-[-0.02em] uppercase">
                Skip
              </p>
              <p className="text-muted mt-1.5 font-serif text-[0.9375rem] leading-snug">
                You’re paying too much for what you get.
              </p>
            </div>
          </div>
        </Step>
      </ol>
    </Section>
  )
}

function Step({
  index,
  title,
  body,
  children,
}: {
  index: string
  title: string
  body: string
  children: React.ReactNode
}) {
  return (
    <li>
      <Reveal delay={Number(index) * 90}>
        <Card className="flex h-full flex-col gap-4 p-5">
          <div className="flex flex-col gap-1.5">
            <span className="tnum text-faint text-[0.6875rem] font-medium tracking-[0.14em]">
              {index}
            </span>
            <h3 className="text-heading text-ink font-semibold">{title}</h3>
            <p className="text-muted text-[0.9375rem] leading-snug">{body}</p>
          </div>
          <div className="mt-auto pt-2">{children}</div>
        </Card>
      </Reveal>
    </li>
  )
}
