import { Section, SectionLabel, SectionTitle } from './section'
import { Reveal } from './reveal'
import { VerdictCard } from '@/components/worth/verdict-card'
import { HERO_EXAMPLE } from '@/lib/analysis/fixtures'
import { SignalList } from '@/components/worth/signal-list'

/** The verdict, at full size, with the reasoning behind it. */
export function VerdictSection() {
  return (
    <Section>
      <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:items-center lg:gap-16">
        <div className="flex flex-col gap-4">
          <SectionLabel>The verdict</SectionLabel>
          <SectionTitle className="max-w-[18ch]">A decision, not a research report.</SectionTitle>
          <p className="text-lead text-muted max-w-[42ch]">
            Worth doesn’t hand you a wall of information and wish you luck. It reaches a conclusion,
            tells you the one thing that drove it, and shows its work underneath.
          </p>

          <div className="border-rule mt-2 border-t pt-5">
            <p className="text-muted mb-3 text-[0.6875rem] font-medium tracking-[0.14em] uppercase">
              Why this verdict
            </p>
            <SignalList signals={HERO_EXAMPLE.result?.signals ?? []} compact />
          </div>
        </div>

        <Reveal>
          <VerdictCard analysis={HERO_EXAMPLE} showSignals={false} />
        </Reveal>
      </div>
    </Section>
  )
}
