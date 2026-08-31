import { Section, Eyebrow, Statement, Disclosure } from './section'
import { ProductImage } from '@/components/worth/product-image'
import { cn } from '@/lib/utils/cn'
import type { Verdict } from '@/lib/analysis/types'

/**
 * Beat 04 — Worth is not an Amazon review checker.
 *
 * Three genuinely different kinds of spend, each shown the way you'd actually
 * meet it: a physical product as a product, software as an interface, a course
 * as a course. Giving all three the same card treatment would have been the
 * easy route and would have quietly said "these are all the same thing".
 *
 * One of the three is a Buy, so Worth doesn't read as reflexively negative.
 */

const VERDICT_STYLE: Record<Verdict, { text: string; wash: string; label: string }> = {
  buy: { text: 'text-buy', wash: 'bg-buy-wash', label: 'Buy' },
  think_twice: { text: 'text-think', wash: 'bg-think-wash', label: 'Think twice' },
  skip: { text: 'text-skip', wash: 'bg-skip-wash', label: 'Skip' },
}

export function PurchaseTypes() {
  return (
    <Section tone="sunk" width="wide">
      <div className="max-w-[34rem]">
        <Eyebrow index="04">Anywhere you spend</Eyebrow>
        <Statement className="mt-5 max-w-[18ch]">A link is a link.</Statement>
        <p className="text-lead text-graphite mt-6">
          Worth doesn’t care whether it’s a product page, a subscription or a course someone sold
          you on TikTok.
        </p>
      </div>

      <div className="scroll-strip -mx-5 mt-12 flex snap-x snap-mandatory gap-4 px-5 sm:mt-16 lg:mx-0 lg:grid lg:grid-cols-3 lg:gap-5 lg:px-0">
        {/* Physical — shown as a product. */}
        <Panel
          kind="Physical product"
          title="Over-ear headphones"
          meta="Audio Store"
          score={61}
          verdict="think_twice"
          line="Good product, wrong price. Same model for €329."
          price="€399"
          best="€329"
        >
          <div className="bg-paper-2 flex h-full items-center justify-center p-6">
            <ProductImage
              asset="headphones"
              sizes="(max-width: 1024px) 60vw, 280px"
              className="aspect-[4/3] w-full max-w-[13rem]"
            />
          </div>
        </Panel>

        {/* Software — shown as an interface. */}
        <Panel
          kind="Software"
          title="Project tool, annual plan"
          meta="Team subscription"
          score={82}
          verdict="buy"
          line="Priced fairly for what you use, and easy to leave."
          price="€96/yr"
          best={null}
        >
          <div className="bg-midnight flex h-full flex-col justify-center gap-2 p-5">
            <div className="flex items-center gap-1.5">
              <span className="size-2 rounded-full bg-white/15" />
              <span className="size-2 rounded-full bg-white/15" />
              <span className="size-2 rounded-full bg-white/15" />
            </div>
            <div className="mt-1 flex gap-2">
              <div className="flex w-1/3 flex-col gap-1.5">
                <span className="h-2 rounded-full bg-white/20" />
                <span className="h-2 w-4/5 rounded-full bg-white/10" />
                <span className="h-2 w-3/5 rounded-full bg-white/10" />
              </div>
              <div className="flex flex-1 flex-col gap-1.5">
                <span className="bg-violet/70 h-2 w-2/3 rounded-full" />
                <span className="h-2 rounded-full bg-white/10" />
                <span className="h-2 w-5/6 rounded-full bg-white/10" />
                <span className="h-2 w-1/2 rounded-full bg-white/10" />
              </div>
            </div>
            <div className="mt-2 flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-2.5 py-2">
              <span className="text-[0.625rem] text-white/45">Annual · per seat</span>
              <span className="tnum text-[0.8125rem] font-semibold text-white">€96</span>
            </div>
          </div>
        </Panel>

        {/* Digital — shown as a course. */}
        <Panel
          kind="Digital product"
          title="“Six-figure freelancing”"
          meta="Online course · 14 modules"
          score={28}
          verdict="skip"
          line="Outcome claims aren’t backed by anything checkable."
          price="€249"
          best={null}
        >
          <div className="bg-paper-2 flex h-full items-center justify-center p-4">
            <ProductImage
              asset="course"
              sizes="(max-width: 1024px) 60vw, 280px"
              className="aspect-[4/3] w-full max-w-[14rem]"
            />
          </div>
        </Panel>
      </div>

      <Disclosure className="mt-6">
        Illustrative examples. Not real analyses, prices, products or recommendations.
      </Disclosure>
    </Section>
  )
}

function Panel({
  kind,
  title,
  meta,
  score,
  verdict,
  line,
  price,
  best,
  children,
}: {
  kind: string
  title: string
  meta: string
  score: number
  verdict: Verdict
  line: string
  price: string
  best: string | null
  children: React.ReactNode
}) {
  const style = VERDICT_STYLE[verdict]

  return (
    <article className="rounded-object border-line bg-surface flex w-[18rem] shrink-0 snap-start flex-col overflow-hidden border lg:w-auto">
      <div className="border-line border-b px-5 py-3">
        <span className="label text-graphite">{kind}</span>
      </div>

      {/* Each type gets the visual treatment it actually has in the world. */}
      <div className="border-line h-44 border-b">{children}</div>

      <div className="flex flex-1 flex-col gap-4 p-5">
        <div>
          <p className="text-ink leading-snug font-medium">{title}</p>
          <p className="text-graphite mt-0.5 text-[0.8125rem]">{meta}</p>
        </div>

        <div className="flex items-baseline gap-2">
          <span
            className={cn(
              'tnum text-xl font-semibold',
              best ? 'text-faint line-through decoration-1' : 'text-ink',
            )}
          >
            {price}
          </span>
          {best && <span className="tnum text-ink text-xl font-semibold">{best}</span>}
        </div>

        <div className="border-line mt-auto flex items-center justify-between gap-3 border-t pt-4">
          <span
            className={cn(
              'rounded-full px-3 py-1.5 text-[0.8125rem] font-semibold tracking-wide uppercase',
              style.wash,
              style.text,
            )}
          >
            {style.label}
          </span>
          <span className="flex items-baseline gap-1">
            <span className={cn('tnum text-2xl font-semibold tracking-[-0.03em]', style.text)}>
              {score}
            </span>
            <span className="tnum text-faint text-[0.6875rem]">/100</span>
          </span>
        </div>

        <p className="text-graphite text-[0.875rem] leading-snug">{line}</p>
      </div>
    </article>
  )
}
