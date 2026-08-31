import { Section, Eyebrow, Statement, Disclosure } from './section'
import { ProductImage } from '@/components/worth/product-image'
import { cn } from '@/lib/utils/cn'
import type { Verdict } from '@/lib/analysis/types'

/**
 * Beat 04 — Worth is not an Amazon review checker.
 *
 * Three genuinely different kinds of spend, each given its own full-width
 * moment down the page. This used to be three identical rounded cards in a
 * horizontal scroller, which was wrong twice over: it made three unlike things
 * look like one thing, and on a phone it hid two thirds of the argument behind
 * a swipe most visitors never make.
 *
 * Now each type is a scene of its own, shown the way you'd actually meet it —
 * a physical product as a photograph, software as an interface, a course as a
 * course — with the verdict set against it as type. They alternate sides on
 * desktop so the page doesn't fall into a rhythm.
 *
 * One of the three is a Buy, so Worth doesn't read as reflexively negative.
 */

const VERDICT_STYLE: Record<Verdict, { text: string; label: string }> = {
  buy: { text: 'text-buy', label: 'Buy' },
  think_twice: { text: 'text-think', label: 'Think twice' },
  skip: { text: 'text-skip', label: 'Skip' },
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

      <div className="mt-14 flex flex-col gap-16 sm:mt-20 sm:gap-24">
        <Moment
          kind="Physical product"
          title="Over-ear noise-cancelling headphones"
          meta="Audio Store"
          score={61}
          verdict="think_twice"
          line="Good product, wrong price. The same model is €329 at a verified retailer."
          price="€399"
          best="€329"
        >
          <ProductImage
            asset="headphones"
            sizes="(max-width: 1024px) 100vw, 560px"
            className="aspect-[4/3] w-full"
          />
        </Moment>

        <Moment
          kind="Software"
          title="Design tool, annual team plan"
          meta="Per seat, billed yearly"
          score={82}
          verdict="buy"
          line="Priced fairly for the seats you actually use, and easy to leave."
          price="€96/yr"
          best={null}
          flip
        >
          <SoftwareScene />
        </Moment>

        <Moment
          kind="Digital product"
          title="“Six-figure freelancing”"
          meta="Online course · 14 modules"
          score={28}
          verdict="skip"
          line="The outcome claims aren’t backed by anything a buyer can check."
          price="€249"
          best={null}
        >
          <ProductImage
            asset="course"
            sizes="(max-width: 1024px) 100vw, 560px"
            className="bg-paper-2 aspect-[4/3] w-full"
          />
        </Moment>
      </div>

      <Disclosure className="mt-14">
        Illustrative examples. Not real analyses, prices, products or recommendations.
      </Disclosure>
    </Section>
  )
}

function Moment({
  kind,
  title,
  meta,
  score,
  verdict,
  line,
  price,
  best,
  flip,
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
  flip?: boolean
  children: React.ReactNode
}) {
  const style = VERDICT_STYLE[verdict]

  return (
    <article className="grid grid-cols-1 items-center gap-8 lg:grid-cols-2 lg:gap-16">
      <div className={cn(flip && 'lg:order-2')}>{children}</div>

      <div className={cn(flip && 'lg:order-1')}>
        <span className="label text-faint">{kind}</span>
        <p className="text-page text-ink mt-4 max-w-[20ch] font-medium">{title}</p>
        <p className="text-graphite mt-2 text-[0.9375rem]">{meta}</p>

        <div className="mt-8 flex items-baseline gap-4">
          <span className={cn('tnum text-figure font-semibold', style.text)}>{score}</span>
          <span className="flex flex-col">
            <span className={cn('text-page font-semibold tracking-[-0.02em]', style.text)}>
              {style.label}
            </span>
            <span className="tnum text-faint text-[0.8125rem]">out of 100</span>
          </span>
        </div>

        <p className="text-lead text-ink-soft mt-6 max-w-[36ch]">{line}</p>

        <div className="border-line mt-6 flex items-baseline gap-3 border-t pt-5">
          <span
            className={cn(
              'tnum text-figure-sm font-semibold',
              best ? 'text-faint line-through decoration-1' : 'text-ink',
            )}
          >
            {price}
          </span>
          {best && (
            <>
              <span aria-hidden className="text-violet">
                →
              </span>
              <span className="tnum text-figure-sm text-ink font-semibold">{best}</span>
            </>
          )}
        </div>
      </div>
    </article>
  )
}

/**
 * Software shown as software: a real-looking pricing surface, not a physical
 * object standing in for one. The visual language changing with the thing being
 * analysed is the whole argument of this section.
 */
function SoftwareScene() {
  return (
    <div className="bg-midnight rounded-object relative overflow-hidden">
      <div className="stage-light absolute inset-0" aria-hidden />
      <div className="relative flex aspect-[4/3] flex-col justify-center gap-4 p-6 sm:p-10">
        <span className="label text-white/40">Team plan</span>

        <p className="tnum text-figure font-semibold text-white">
          €8<span className="text-[0.3em] font-normal text-white/40"> /seat/mo</span>
        </p>

        <ul className="mt-2 flex flex-col gap-2.5">
          {['12 seats active', '3 seats unused for 90 days', 'Cancel any time'].map((row, i) => (
            <li key={row} className="flex items-center gap-2.5 text-[0.9375rem] text-white/70">
              <span
                aria-hidden
                className={cn('size-1.5 rounded-full', i === 1 ? 'bg-think-lift' : 'bg-buy-lift')}
              />
              {row}
            </li>
          ))}
        </ul>

        <div className="mt-4 flex items-center justify-between border-t border-white/10 pt-4">
          <span className="text-[0.8125rem] text-white/45">Billed annually</span>
          <span className="tnum text-[1.125rem] font-semibold text-white">€96/yr</span>
        </div>
      </div>
    </div>
  )
}
