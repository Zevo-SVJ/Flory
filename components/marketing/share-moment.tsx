import { Section, Eyebrow, Statement, Disclosure } from './section'
import { ShareCard } from '@/components/worth/share-card'
import { PRIMARY_EXAMPLE } from '@/lib/analysis/fixtures'

/**
 * Beat 08 — the result travels.
 *
 * The card is the subject, so the copy stays out of its way. The privacy line
 * is here rather than in a footnote because it's the reason someone would be
 * willing to post one.
 */
export function ShareMoment() {
  return (
    <Section tone="dark" glow>
      <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1fr)] lg:gap-20">
        <div className="order-2 lg:order-1">
          <Eyebrow index="08" tone="dark">
            And it travels
          </Eyebrow>
          <Statement tone="dark" className="mt-5 max-w-[16ch]">
            A verdict is a good story.
          </Statement>

          <p className="text-lead mt-6 max-w-[44ch] text-white/55">
            “I almost spent €399 on these” is a better opening line than any ad Worth could buy.
            Every result is built to hold up on its own — in a feed, a group chat, a reply.
          </p>

          <p className="mt-5 max-w-[44ch] text-[0.9375rem] leading-relaxed text-white/45">
            A shared card carries the verdict and the money and nothing else. Not the link you
            pasted, not what else you’ve looked at, not who you are.
          </p>

          <Disclosure tone="dark" className="mt-6">
            Public sharing is still being built.
          </Disclosure>
        </div>

        <div className="order-1 lg:order-2">
          <div className="mx-auto w-full max-w-[21rem] lg:mr-0 lg:ml-auto">
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
