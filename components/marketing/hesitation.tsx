import { Section, Beat } from './section'
import { cn } from '@/lib/utils/cn'

/**
 * Beats 01–03: you found something, you hesitated, Worth checked.
 *
 * The composition is the argument. The same four questions appear twice —
 * unanswered on the left in grey, answered on the right in ink with Worth's
 * findings — so the reader sees the product's value as a transformation
 * rather than as a claim about it. No feature list, no icons.
 */

const QUESTIONS = [
  { q: 'Is €399 a good price?', a: '€329 at three other authorised retailers.', tone: 'negative' },
  { q: 'Are the reviews trustworthy?', a: '2,140 read. Battery life holds up.', tone: 'positive' },
  {
    q: 'Can I trust this seller?',
    a: 'Authorised, 30-day returns, 2-year warranty.',
    tone: 'positive',
  },
  { q: 'Is there something better?', a: 'Same model, same warranty, €70 less.', tone: 'positive' },
] as const

const DOT = {
  positive: 'bg-buy',
  negative: 'bg-skip',
} as const

export function Hesitation() {
  return (
    <Section>
      <div className="flex flex-col gap-3">
        <Beat index="01">You found something</Beat>
        <Statement />
      </div>

      <div className="mt-12 grid grid-cols-1 gap-10 lg:mt-16 lg:grid-cols-2 lg:gap-14">
        {/* Before. */}
        <div>
          <div className="flex items-center gap-2.5">
            <span className="label text-graphite">Open tabs, no answer</span>
            <span className="bg-line h-px flex-1" />
          </div>
          <ul className="mt-5 flex flex-col gap-px">
            {QUESTIONS.map(({ q }) => (
              <li
                key={q}
                className="border-line text-faint flex items-center gap-3 border-l-2 py-3 pl-4 text-[0.9375rem]"
              >
                <span className="text-line-strong font-serif text-lg">?</span>
                {q}
              </li>
            ))}
          </ul>
        </div>

        {/* After. */}
        <div>
          <div className="flex items-center gap-2.5">
            <span className="label text-worth">Worth checked</span>
            <span className="bg-worth-line h-px flex-1" />
          </div>
          <ul className="mt-5 flex flex-col gap-px">
            {QUESTIONS.map(({ q, a, tone }) => (
              <li key={q} className="border-worth border-l-2 py-3 pl-4">
                <p className="text-graphite text-[0.8125rem]">{q}</p>
                <p className="text-ink mt-1 flex items-start gap-2 text-[0.9375rem] font-medium">
                  <span
                    className={cn('mt-[7px] size-1.5 shrink-0 rounded-full', DOT[tone])}
                    aria-hidden
                  />
                  {a}
                </p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Section>
  )
}

function Statement() {
  return (
    <h2 className="text-statement text-ink max-w-[24ch] font-serif font-medium">
      You hesitated. That hesitation is worth money.
    </h2>
  )
}
