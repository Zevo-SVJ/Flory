import { Section } from './section'
import { Reveal } from './reveal'

/**
 * The category difference, in two lines.
 *
 * Most shopping tools are search tools. Worth is a decision tool. No competitor
 * is named — the contrast does the work.
 */
export function Differentiation() {
  return (
    <Section bleed>
      <div className="mx-auto flex max-w-3xl flex-col gap-8">
        <Reveal>
          <p className="text-heading text-faint font-serif leading-snug font-normal">
            Most shopping tools help you find products.
          </p>
        </Reveal>
        <Reveal delay={140}>
          <p className="text-title text-ink font-serif leading-[1.15] font-medium">
            Worth helps you decide whether the one you’re looking at is worth your money.
          </p>
        </Reveal>
      </div>
    </Section>
  )
}
