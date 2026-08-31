import { Disclosure } from './section'
import { cn } from '@/lib/utils/cn'

/**
 * Beat 02 — the turn.
 *
 * One scene, edge to edge, instead of a grid of cards. The visitor's own
 * research floats in the dark at different depths and scales: a rating with no
 * context, a forum opinion, a price with nothing to compare it to. It is
 * deliberately unresolved and slightly out of reach — that is what having
 * twelve tabs open actually feels like.
 *
 * Then the noise stops and one line answers it. The verdict is set as type at
 * display size, not as a panel, because a panel would make Worth's answer look
 * like one more fragment rather than the thing that ends them.
 */

interface Fragment {
  text: string
  sub: string
  /** Position, scale and blur together do the depth. */
  place: string
  depth: 'near' | 'mid' | 'far'
}

const FRAGMENTS: Fragment[] = [
  { text: '4.4 ★', sub: '2,140 ratings', place: 'left-[3%] top-[4%]', depth: 'near' },
  { text: '“Best I’ve owned”', sub: 'forum, 2024', place: 'right-[5%] top-[10%]', depth: 'mid' },
  { text: '€399', sub: 'this seller', place: 'left-[14%] top-[30%]', depth: 'near' },
  { text: '“Overpriced”', sub: 'one review', place: 'right-[2%] top-[34%]', depth: 'far' },
  { text: '18 min video', sub: 'sponsored?', place: 'left-[2%] top-[54%]', depth: 'far' },
  { text: '€349', sub: 'different model', place: 'right-[16%] top-[58%]', depth: 'mid' },
  { text: '3 sellers', sub: 'unverified', place: 'left-[20%] top-[76%]', depth: 'mid' },
  { text: '“Hinge broke”', sub: 'previous gen', place: 'right-[4%] top-[80%]', depth: 'near' },
]

const DEPTH = {
  near: 'scale-100 opacity-90',
  mid: 'scale-[0.88] opacity-60 blur-[0.4px]',
  far: 'scale-[0.76] opacity-35 blur-[1.2px]',
} as const

export function ShouldYouBuy() {
  return (
    <section className="scene scene-in scene-out relative overflow-hidden">
      {/* The noise. A field the reader has to look through. */}
      <div className="relative mx-auto h-[26rem] w-full max-w-4xl sm:h-[30rem]">
        {FRAGMENTS.map((f) => (
          <div
            key={f.text}
            aria-hidden
            className={cn('absolute max-w-[9rem] sm:max-w-none', f.place, DEPTH[f.depth])}
          >
            <p className="text-[0.9375rem] leading-tight font-medium text-white/75 sm:text-[1.0625rem]">
              {f.text}
            </p>
            <p className="text-[0.6875rem] text-white/35">{f.sub}</p>
          </div>
        ))}

        {/* The question, sitting in the middle of the noise. */}
        <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 px-6 text-center">
          <p className="label text-violet-lift">02 · But should you buy it?</p>
          <p className="text-statement mx-auto mt-4 max-w-[14ch] font-serif font-medium text-white">
            Twelve tabs. No answer.
          </p>
        </div>
      </div>

      {/* The resolution, as type. */}
      <div className="relative mx-auto max-w-4xl px-5 pb-20 text-center sm:px-6 sm:pb-24">
        <div className="mx-auto h-16 w-px bg-gradient-to-b from-transparent via-white/20 to-transparent" />

        <p className="text-lead mx-auto mt-8 max-w-[30ch] text-white/50">
          Worth reads all of it, and answers in one line.
        </p>

        {/* The one line. Deliberately not a score — the number is beat 05's
            job, and running the same 61 reveal three times down one page turns
            the page's biggest moment into a motif. */}
        <p className="text-figure mx-auto mt-10 max-w-[15ch] font-serif font-medium text-white">
          Good product. Wrong price.
        </p>
        <p className="text-lead mx-auto mt-8 max-w-[32ch] text-white/60">
          €70 above the best verified price, from one of eleven sellers carrying the same model.
        </p>

        <Disclosure tone="dark" className="mt-10">
          Illustrative analysis — not real research.
        </Disclosure>
      </div>
    </section>
  )
}
