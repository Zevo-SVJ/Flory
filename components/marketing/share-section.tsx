import { Section, SectionLabel, SectionTitle } from './section'
import { Reveal } from './reveal'
import { ShareCard } from '@/components/worth/share-card'
import { SHARE_EXAMPLE } from '@/lib/analysis/fixtures'

/**
 * The share card.
 *
 * Every Worth result is designed to survive being screenshotted into a feed:
 * portrait, high contrast, verdict legible at thumbnail size. Sharing is not
 * wired up yet and this section does not suggest otherwise.
 */
export function ShareSection() {
  return (
    <Section>
      <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.85fr)] lg:items-center lg:gap-16">
        <div className="flex flex-col gap-4">
          <SectionLabel>Shareable results</SectionLabel>
          <SectionTitle className="max-w-[20ch]">Worth a screenshot, by design.</SectionTitle>
          <p className="text-lead text-muted max-w-[44ch]">
            A verdict is a story: what you almost bought, what it was really worth, and what you did
            instead. Every result is laid out to hold up on its own in a feed, a group chat or a
            reply.
          </p>
          <p className="text-muted max-w-[44ch] text-[0.9375rem]">
            Public sharing is still being built. When it ships, a shared result will show the
            verdict and the money — never the link you pasted or anything else about you.
          </p>
        </div>

        <Reveal>
          <div className="mx-auto w-full max-w-[19rem]">
            <ShareCard
              score={SHARE_EXAMPLE.score ?? 0}
              verdict={SHARE_EXAMPLE.verdict ?? 'skip'}
              title={SHARE_EXAMPLE.title}
              summary={SHARE_EXAMPLE.summary}
              priceMinor={SHARE_EXAMPLE.priceMinor}
              bestPriceMinor={SHARE_EXAMPLE.bestPriceMinor}
              currency={SHARE_EXAMPLE.currency}
            />
          </div>
        </Reveal>
      </div>
    </Section>
  )
}
