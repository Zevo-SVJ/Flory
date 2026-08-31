import { Section, Beat } from './section'
import { ShareCard } from '@/components/worth/share-card'
import { PRIMARY_EXAMPLE } from '@/lib/analysis/fixtures'

/**
 * Beat 06 — the result travels.
 *
 * The card is the hero of this section, so the copy stays out of its way. The
 * claim about privacy is here rather than in a footnote because it's the
 * reason someone would be willing to post one.
 */
export function ShareMoment() {
  return (
    <Section>
      <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1fr)] lg:gap-16">
        <div className="order-2 lg:order-1">
          <div className="flex flex-col gap-3">
            <Beat index="06">And it travels</Beat>
            <h2 className="text-statement text-ink max-w-[20ch] font-serif font-medium">
              A verdict is a good story.
            </h2>
          </div>

          <p className="text-lead text-graphite mt-5 max-w-[46ch]">
            “I almost spent €399 on these” is a better opening line than any ad Worth could buy.
            Every result is built to hold up on its own — in a feed, a group chat, a reply.
          </p>

          <p className="text-graphite mt-4 max-w-[46ch] text-[0.9375rem] leading-relaxed">
            A shared card carries the verdict and the money and nothing else. Not the link you
            pasted, not what else you’ve looked at, not who you are.
          </p>

          <p className="text-faint mt-5 text-[0.75rem]">Public sharing is still being built.</p>
        </div>

        <div className="order-1 lg:order-2">
          <div className="mx-auto w-full max-w-[22rem] lg:mr-0 lg:ml-auto">
            <ShareCard
              score={PRIMARY_EXAMPLE.score ?? 61}
              verdict={PRIMARY_EXAMPLE.verdict ?? 'think_twice'}
              title={PRIMARY_EXAMPLE.title}
              summary={PRIMARY_EXAMPLE.summary}
              priceMinor={PRIMARY_EXAMPLE.priceMinor}
              bestPriceMinor={PRIMARY_EXAMPLE.bestPriceMinor}
              currency={PRIMARY_EXAMPLE.currency}
            />
          </div>
        </div>
      </div>
    </Section>
  )
}
