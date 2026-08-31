import { Section, Beat } from './section'
import { CATEGORY_EXAMPLES, type CategoryExample } from '@/lib/analysis/fixtures'
import { VERDICT_LABEL } from '@/lib/analysis/verdict'
import { ScoreMeter } from '@/components/worth/score-meter'
import { cn } from '@/lib/utils/cn'

/**
 * Worth is not an Amazon review checker.
 *
 * Three different kinds of spend, each with a different verdict — including a
 * "buy", so the product doesn't read as reflexively negative. On mobile these
 * become a snapping horizontal strip rather than a third stacked card, which
 * keeps the comparison between them legible.
 */
export function Categories() {
  return (
    <Section>
      <div className="flex flex-col gap-3">
        <Beat index="02">Anywhere you spend</Beat>
        <h2 className="text-statement text-ink max-w-[26ch] font-serif font-medium">
          A link is a link. Worth doesn’t care where you’re about to spend.
        </h2>
      </div>

      <div className="scroll-strip -mx-4 mt-10 flex snap-x snap-mandatory gap-4 px-4 sm:mt-14 sm:gap-5 lg:mx-0 lg:grid lg:grid-cols-3 lg:px-0">
        {CATEGORY_EXAMPLES.map((example) => (
          <CategoryPanel key={example.id} example={example} />
        ))}
      </div>

      <p className="text-faint mt-5 text-[0.75rem]">
        Illustrative examples. Not real analyses, prices or recommendations.
      </p>
    </Section>
  )
}

function CategoryPanel({ example }: { example: CategoryExample }) {
  const verdictText =
    example.verdict === 'buy'
      ? 'text-buy'
      : example.verdict === 'think_twice'
        ? 'text-think'
        : 'text-skip'

  return (
    <article
      className={cn(
        'rounded-object border-line bg-surface flex w-[17rem] shrink-0 snap-start flex-col border',
        'lg:w-auto',
      )}
    >
      <div className="border-line flex items-center justify-between gap-3 border-b px-4 py-3">
        <span className="label text-graphite">{example.kind}</span>
      </div>

      <div className="flex flex-1 flex-col gap-4 p-4 sm:p-5">
        <div>
          <p className="text-ink leading-snug font-medium">{example.title}</p>
          <p className="text-graphite mt-0.5 text-[0.8125rem]">{example.meta}</p>
        </div>

        <div className="flex items-baseline gap-2">
          <span
            className={cn(
              'tnum text-ink text-xl font-semibold',
              example.bestPrice && 'text-faint line-through decoration-1',
            )}
          >
            {example.price}
          </span>
          {example.bestPrice && (
            <span className="tnum text-ink text-xl font-semibold">{example.bestPrice}</span>
          )}
        </div>

        <div className="border-line mt-auto flex flex-col gap-3 border-t pt-4">
          <p
            className={cn(
              'text-lg leading-none font-semibold tracking-[-0.02em] uppercase',
              verdictText,
            )}
          >
            {VERDICT_LABEL[example.verdict]}
          </p>
          <ScoreMeter score={example.score} verdict={example.verdict} size="sm" />
          <p className="text-graphite text-[0.875rem] leading-snug">{example.line}</p>
        </div>
      </div>
    </article>
  )
}
