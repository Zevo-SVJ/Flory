import { Section, Eyebrow, Statement, Disclosure } from './section'
import { cn } from '@/lib/utils/cn'

/**
 * Beat 07 — Worth as a product you'd actually use.
 *
 * A phone frame showing the real flow: link pasted, checks running, verdict.
 * Three states side by side rather than one screenshot, because the point is
 * the sequence — the visitor should be able to follow what using Worth is like
 * without reading a paragraph about it.
 *
 * These are real components' visual language, not a stock dashboard mock.
 */
export function ProductDemo() {
  return (
    <Section tone="sunk" width="wide">
      <div className="max-w-[34rem]">
        <Eyebrow index="07">Using it</Eyebrow>
        <Statement className="mt-5 max-w-[18ch]">Paste the link. Get the verdict.</Statement>
        <p className="text-lead text-graphite mt-6">
          No extension to install, no store to shop in, nothing to learn.
        </p>
      </div>

      <div className="scroll-strip -mx-5 mt-12 flex snap-x snap-mandatory gap-5 px-5 sm:mt-16 lg:mx-0 lg:grid lg:grid-cols-3 lg:gap-8 lg:px-0">
        <Phone step="01" caption="Paste anything you're about to buy.">
          <div className="flex h-full flex-col gap-3.5 px-4 pt-9">
            <p className="text-ink font-serif text-[1.375rem] leading-tight">
              Is it worth your money?
            </p>
            <div className="border-violet flex items-center gap-2 rounded-full border bg-white px-2.5 py-2 shadow-[0_0_0_4px_var(--color-violet-wash)]">
              <span className="text-ink truncate text-[0.6875rem]">audio-store.example/…</span>
              <span className="bg-violet ml-auto shrink-0 rounded-full px-2.5 py-1 text-[0.625rem] font-semibold text-white">
                Analyze
              </span>
            </div>
            <p className="text-graphite text-[0.625rem]">No link? Upload a screenshot.</p>

            <span className="label text-faint mt-2">Category</span>
            <div className="flex flex-wrap gap-1.5">
              {['Product', 'Software', 'Course', 'Other'].map((c, i) => (
                <span
                  key={c}
                  className={cn(
                    'rounded-full border px-2.5 py-1 text-[0.625rem]',
                    i === 0 ? 'border-violet bg-violet text-white' : 'border-line text-graphite',
                  )}
                >
                  {c}
                </span>
              ))}
            </div>

            <span className="label text-faint mt-2">Recent</span>
            <div className="flex flex-col gap-1.5">
              {[
                ['82', 'Project tool', 'text-buy'],
                ['28', 'Online course', 'text-skip'],
              ].map(([score, name, tone]) => (
                <div
                  key={name}
                  className="border-line flex items-center gap-2 rounded-lg border bg-white px-2 py-1.5"
                >
                  <span className={cn('tnum text-[0.75rem] font-semibold', tone)}>{score}</span>
                  <span className="text-graphite truncate text-[0.625rem]">{name}</span>
                </div>
              ))}
            </div>
          </div>
        </Phone>

        <Phone step="02" caption="Worth checks the things that matter.">
          <div className="flex h-full flex-col gap-2.5 px-4 pt-9">
            <p className="text-ink font-serif text-[1.0625rem] leading-tight">Checking 6 things…</p>
            <div className="bg-line mb-1 h-1 w-full overflow-hidden rounded-full">
              <span className="bg-violet block h-full w-1/2 rounded-full" />
            </div>
            {[
              ['Price', true],
              ['Reviews', true],
              ['Trust', true],
              ['Value', false],
              ['Risk', false],
              ['Alternatives', false],
            ].map(([label, done]) => (
              <div key={label as string} className="flex items-center gap-2.5">
                <span
                  className={cn(
                    'flex size-4 shrink-0 items-center justify-center rounded-full',
                    done ? 'bg-violet' : 'border-line-strong border',
                  )}
                >
                  {done && (
                    <svg width="8" height="8" viewBox="0 0 10 10" fill="none">
                      <path
                        d="m1.6 5.2 2.2 2.2L8.4 2.8"
                        stroke="#fff"
                        strokeWidth="2"
                        strokeLinecap="square"
                      />
                    </svg>
                  )}
                </span>
                <span className={cn('text-[0.75rem]', done ? 'text-ink' : 'text-faint')}>
                  {label}
                </span>
                {done && <span className="bg-violet/25 ml-auto h-1 w-8 rounded-full" />}
              </div>
            ))}

            {/* Findings land as each check completes, so the screen fills the
                way it would in use rather than leaving a blank half. */}
            <span className="label text-faint mt-3">Found so far</span>
            <div className="flex flex-col gap-1.5">
              {[
                ['€329', 'at a verified retailer', 'text-buy'],
                ['2,140', 'reviews read', 'text-ink'],
                ['11', 'sellers compared', 'text-ink'],
              ].map(([v, k, tone]) => (
                <div
                  key={k}
                  className="border-line flex items-baseline gap-1.5 rounded-lg border bg-white px-2 py-1.5"
                >
                  <span className={cn('tnum text-[0.75rem] font-semibold', tone)}>{v}</span>
                  <span className="text-graphite truncate text-[0.625rem]">{k}</span>
                </div>
              ))}
            </div>
          </div>
        </Phone>

        <Phone step="03" caption="One answer, with the evidence under it.">
          <div className="flex h-full flex-col gap-3 px-4 pt-9">
            <span className="label text-faint">Worth verdict</span>
            <div className="flex items-end gap-1.5">
              <span className="tnum text-think text-4xl leading-none font-semibold tracking-[-0.05em]">
                61
              </span>
              <span className="tnum text-faint pb-0.5 text-[0.625rem]">/100</span>
            </div>
            <p className="text-think text-lg leading-none font-semibold tracking-[-0.02em] uppercase">
              Think twice
            </p>
            <p className="text-ink font-serif text-[0.875rem] leading-snug">
              The product is good. The price isn’t.
            </p>
            <div className="bg-buy-wash flex items-baseline gap-1.5 rounded-lg px-2.5 py-2">
              <span className="tnum text-faint text-[0.6875rem] line-through">€399</span>
              <span className="tnum text-ink text-[0.9375rem] font-semibold">€329</span>
              <span className="tnum text-buy ml-auto text-[0.6875rem] font-semibold">−€70</span>
            </div>

            <span className="label text-faint mt-1">Why</span>
            <ul className="flex flex-col gap-1.5">
              {[
                ['Price', '€70 above best', 'bg-skip'],
                ['Reviews', 'Battery praised', 'bg-buy'],
                ['Trust', 'Verified seller', 'bg-buy'],
                ['Risk', 'Refresh expected', 'bg-think'],
              ].map(([k, v, dot]) => (
                <li key={k} className="flex items-start gap-1.5">
                  <span className={cn('mt-1 size-1 shrink-0 rounded-full', dot)} />
                  <span className="text-graphite text-[0.625rem] leading-tight">
                    <span className="text-ink font-semibold">{k}</span> · {v}
                  </span>
                </li>
              ))}
            </ul>

            <div className="bg-violet mt-auto mb-3 flex items-center justify-center rounded-full py-2 text-[0.6875rem] font-semibold text-white">
              Share this verdict
            </div>
          </div>
        </Phone>
      </div>

      <Disclosure className="mt-6">
        Illustrative screens. The research engine isn’t connected yet.
      </Disclosure>
    </Section>
  )
}

/** A phone frame. Real device proportions so the screens read as screens. */
function Phone({
  step,
  caption,
  children,
}: {
  step: string
  caption: string
  children: React.ReactNode
}) {
  return (
    <figure className="flex w-[15rem] shrink-0 snap-start flex-col gap-5 lg:w-auto">
      <div className="relative mx-auto w-full max-w-[15rem]">
        <div className="border-ink bg-ink shadow-lift rounded-[2rem] border-[6px] p-0">
          <div className="bg-paper relative aspect-[9/16] overflow-hidden rounded-[1.55rem]">
            {/* Notch + status bar */}
            <span
              className="bg-ink absolute top-2 left-1/2 z-10 h-4 w-16 -translate-x-1/2 rounded-full"
              aria-hidden
            />
            <div
              className="text-ink absolute inset-x-0 top-0 z-0 flex items-center justify-between px-4 pt-2.5 text-[0.5625rem] font-semibold"
              aria-hidden
            >
              <span className="tnum">9:41</span>
              <span className="flex items-center gap-1">
                <span className="flex items-end gap-px">
                  {[3, 5, 7, 9].map((h) => (
                    <span key={h} className="bg-ink w-[2px] rounded-sm" style={{ height: h }} />
                  ))}
                </span>
                <span className="border-ink/60 h-2 w-4 rounded-[2px] border p-px">
                  <span className="bg-ink block h-full w-2/3 rounded-[1px]" />
                </span>
              </span>
            </div>
            {children}
          </div>
        </div>
      </div>
      <figcaption className="flex gap-2.5">
        <span className="tnum label text-violet shrink-0">{step}</span>
        <span className="text-graphite text-[0.875rem] leading-snug">{caption}</span>
      </figcaption>
    </figure>
  )
}
