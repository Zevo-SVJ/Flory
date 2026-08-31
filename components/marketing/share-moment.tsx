import { Disclosure } from './section'
import { ShareCard } from '@/components/worth/share-card'
import { PRIMARY_EXAMPLE } from '@/lib/analysis/fixtures'

/**
 * Beat 08 — the result travels.
 *
 * The card is the subject, so it gets the middle of a dark scene at the size
 * someone would actually see it at in a feed, and the copy gets out of its way.
 *
 * The loop underneath is shown as the four things that actually happen, in
 * order, rather than drawn as a diagram with arrows — a diagram would be an
 * explanation of a mechanism, and the mechanism here is just: the card is good
 * enough to post, and the next person wants their own.
 *
 * The privacy line is here rather than in a footnote because it is the reason
 * someone would be willing to post one at all.
 */

const LOOP = [
  ['Check something', 'You paste a link before you spend.'],
  ['Get a verdict', 'A number, a call, and the money.'],
  ['Post it', 'The card holds up on its own, with no context.'],
  ['Someone else checks', 'They want to know about their own basket.'],
] as const

export function ShareMoment() {
  return (
    <section className="scene scene-in scene-out relative overflow-hidden py-24 sm:py-32">
      <div className="relative mx-auto max-w-3xl px-5 text-center sm:px-6">
        <p className="label text-white/40">08 · And it travels</p>
        <p className="text-statement mx-auto mt-6 max-w-[16ch] font-serif font-medium text-white">
          A verdict is a good story.
        </p>
        <p className="text-lead mx-auto mt-6 max-w-[42ch] text-white/55">
          “I almost spent €399 on these” is a better opening line than any ad Worth could buy.
        </p>
      </div>

      {/* The object itself, at the size it travels at. */}
      <div className="relative mx-auto mt-14 w-full max-w-[22rem] px-5 sm:mt-16 sm:max-w-[24rem] sm:px-0">
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

      {/* The loop, as what happens rather than as a diagram. */}
      <ol className="relative mx-auto mt-16 grid max-w-4xl grid-cols-1 gap-px overflow-hidden px-5 sm:mt-20 sm:grid-cols-2 sm:px-6 lg:grid-cols-4">
        {LOOP.map(([title, detail], i) => (
          <li key={title} className="border-t border-white/10 py-6 sm:pr-6">
            <span className="tnum label text-violet-lift">0{i + 1}</span>
            <p className="mt-3 text-[1.0625rem] font-medium text-white">{title}</p>
            <p className="mt-1.5 text-[0.9375rem] leading-snug text-white/50">{detail}</p>
          </li>
        ))}
      </ol>

      <div className="relative mx-auto mt-12 max-w-3xl px-5 text-center sm:px-6">
        <p className="mx-auto max-w-[46ch] text-[0.9375rem] leading-relaxed text-white/45">
          A shared card carries the verdict and the money and nothing else. Not the link you
          pasted, not what else you’ve looked at, not who you are.
        </p>

        <Disclosure tone="dark" className="mt-6">
          Public sharing is still being built.
        </Disclosure>
      </div>
    </section>
  )
}
