import { Section, Eyebrow, Statement, Disclosure } from './section'
import { cn } from '@/lib/utils/cn'

/**
 * Beat 02 — the turn.
 *
 * The internet's answer is scattered across sources that don't agree and don't
 * add up. Worth's answer is one line. The composition makes that argument
 * literally: eight fragments of half-information on the left, converging into a
 * single verdict on the right.
 *
 * The fragments are deliberately unresolved — a rating with no context, a
 * forum opinion, a price with no comparison. That's what the reader actually
 * has before Worth.
 */

const SCATTER = [
  { text: '4.4 stars', sub: '2,140 ratings', rot: '-rotate-2' },
  { text: '“Best I’ve owned”', sub: 'forum, 2024', rot: 'rotate-1' },
  { text: '€399', sub: 'this seller', rot: 'rotate-2' },
  { text: '“Overpriced”', sub: 'one review', rot: '-rotate-1' },
  { text: '18 min video', sub: 'sponsored?', rot: 'rotate-1' },
  { text: '€349', sub: 'different model', rot: '-rotate-2' },
  { text: '3 sellers', sub: 'unverified', rot: 'rotate-1' },
  { text: '“Hinge broke”', sub: 'previous gen', rot: '-rotate-1' },
]

export function ShouldYouBuy() {
  return (
    <Section tone="dark" glow>
      <Eyebrow index="02" tone="dark">
        But should you buy it?
      </Eyebrow>

      <div className="mt-6 grid grid-cols-1 gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.85fr)] lg:items-center lg:gap-16">
        <div>
          <Statement tone="dark" className="max-w-[15ch]">
            The internet gives you information.
          </Statement>
          <Statement tone="dark" className="text-violet-lift mt-3 max-w-[15ch]">
            Worth gives you a decision.
          </Statement>

          {/* The scatter. */}
          <div className="mt-10 flex flex-wrap gap-2.5">
            {SCATTER.map((item) => (
              <div
                key={item.text}
                className={cn(
                  'rounded-lg border border-white/8 bg-white/[0.04] px-3 py-2',
                  item.rot,
                )}
              >
                <p className="text-[0.875rem] font-medium text-white/70">{item.text}</p>
                <p className="text-[0.6875rem] text-white/30">{item.sub}</p>
              </div>
            ))}
          </div>

          <p className="text-lead mt-8 max-w-[42ch] text-white/55">
            Eight half-answers that don’t agree with each other. None of them tell you whether to
            spend the €399.
          </p>
        </div>

        {/* The resolution. */}
        <div className="relative">
          <div className="rounded-object border-violet/30 from-violet/[0.16] border bg-gradient-to-b to-transparent p-6 sm:p-8">
            <span className="label text-violet-lift">Worth</span>

            <div className="mt-6 flex items-end gap-2.5">
              <span className="tnum text-[4.5rem] leading-[0.82] font-semibold tracking-[-0.055em] text-white sm:text-[5.5rem]">
                61
              </span>
              <span className="tnum pb-2 text-sm font-medium text-white/40">/100</span>
            </div>

            <p className="text-think-lift mt-4 text-2xl leading-none font-semibold tracking-[-0.02em] uppercase">
              Think twice
            </p>

            <p className="mt-4 font-serif text-xl leading-snug text-white">
              The product is good. The price isn’t.
            </p>

            <ul className="mt-6 flex flex-col gap-2.5 border-t border-white/10 pt-5">
              {[
                ['Same model, verified retailer', '€329'],
                ['Reviews checked', '2,140'],
                ['Sellers compared', '11'],
              ].map(([k, v]) => (
                <li key={k} className="flex items-baseline justify-between gap-4">
                  <span className="text-[0.875rem] text-white/50">{k}</span>
                  <span className="tnum text-[0.9375rem] font-semibold text-white">{v}</span>
                </li>
              ))}
            </ul>
          </div>

          <Disclosure tone="dark" className="mt-4">
            Illustrative analysis — not real research.
          </Disclosure>
        </div>
      </div>
    </Section>
  )
}
