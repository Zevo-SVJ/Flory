import { Section } from './section'
import { Reveal } from './reveal'

const TABS = [
  'reddit.com/r/headphones',
  'amazon.de · reviews',
  'youtube.com · 22 min review',
  'trustpilot.com',
  'idealo.de · price history',
  'forum thread, 2023',
  'another retailer',
  'a comparison blog',
]

/**
 * The problem, stated once.
 *
 * Deliberately under-written — one sentence and a visual of the research nobody
 * wants to do. Explaining this at length would undercut the point.
 */
export function Problem() {
  return (
    <Section bleed>
      <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] lg:items-center lg:gap-16">
        <Reveal>
          <p className="text-title text-ink font-serif leading-[1.15] font-medium">
            You shouldn’t need 12 tabs, 40 reviews and three Reddit threads to decide whether
            something is worth your money.
          </p>
        </Reveal>

        <Reveal delay={120}>
          <div className="relative" aria-hidden>
            <ul className="flex flex-col gap-1.5">
              {TABS.map((tab, index) => (
                <li
                  key={tab}
                  className="rounded-chip border-rule bg-surface flex items-center gap-2.5 border px-3 py-2"
                  style={{ opacity: 1 - index * 0.11 }}
                >
                  <span className="bg-faint size-1.5 shrink-0 rounded-full" />
                  <span className="text-muted truncate text-[0.8125rem]">{tab}</span>
                </li>
              ))}
            </ul>
            <div className="from-paper-sunk pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t to-transparent" />
          </div>
        </Reveal>
      </div>
    </Section>
  )
}
