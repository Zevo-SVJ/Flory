import { Section, Eyebrow, Statement, Disclosure } from './section'
import { ProductImage } from '@/components/worth/product-image'

/**
 * Beat 01 — the moment before Worth.
 *
 * Deliberately quiet and almost copy-free: a product, a price, a seller, a
 * rating. It's a listing, presented as a listing. The reader recognises the
 * situation without being told about it, which is what makes the next section's
 * turn land.
 */
export function FoundSomething() {
  return (
    <Section tone="sunk">
      <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-2 lg:gap-20">
        <div className="order-2 lg:order-1">
          <Eyebrow index="01">You found something</Eyebrow>
          <Statement className="mt-5 max-w-[16ch]">You found something you want.</Statement>
          <p className="text-lead text-graphite mt-6 max-w-[38ch]">
            It looks right. The reviews look fine. The price looks… like a price.
          </p>
        </div>

        {/* The listing, as you'd meet it. */}
        <div className="order-1 lg:order-2">
          <div className="rounded-object border-line bg-surface shadow-object mx-auto max-w-[26rem] overflow-hidden border">
            <div className="border-line flex items-center gap-2 border-b px-4 py-2.5">
              <span className="bg-line-strong size-2 rounded-full" aria-hidden />
              <span className="bg-line-strong size-2 rounded-full" aria-hidden />
              <span className="bg-line-strong size-2 rounded-full" aria-hidden />
              <span className="text-faint ml-2 truncate text-[0.75rem]">
                audio-store.example/headphones
              </span>
            </div>

            <ProductImage
              asset="headphones"
              sizes="(max-width: 1024px) 90vw, 420px"
              className="aspect-[4/3] w-full border-b border-line"
            />

            <div className="flex flex-col gap-3 p-5">
              <div>
                <p className="text-ink font-medium">Over-ear noise-cancelling headphones</p>
                <p className="text-graphite mt-0.5 text-[0.875rem]">Audio Store · In stock</p>
              </div>

              <div className="flex items-center gap-2">
                <Stars />
                <span className="text-graphite text-[0.8125rem]">4.4 · 2,140 ratings</span>
              </div>

              <div className="border-line flex items-baseline justify-between gap-3 border-t pt-3">
                <span className="tnum text-figure-sm text-ink font-semibold tracking-[-0.035em]">
                  €399
                </span>
                <span className="bg-ink rounded-full px-4 py-2 text-[0.8125rem] font-medium text-white">
                  Add to basket
                </span>
              </div>
            </div>
          </div>

          <Disclosure className="mt-4 text-center lg:text-left">
            Illustrative listing. Not a real product, price or seller.
          </Disclosure>
        </div>
      </div>
    </Section>
  )
}

function Stars() {
  return (
    <span className="flex gap-0.5" aria-hidden>
      {[0, 1, 2, 3, 4].map((i) => (
        <svg key={i} width="13" height="13" viewBox="0 0 14 14" fill="none">
          <path
            d="M7 1.5 8.7 5l3.8.5-2.8 2.7.7 3.8L7 10.2 3.6 12l.7-3.8L1.5 5.5 5.3 5 7 1.5Z"
            fill={i < 4 ? 'var(--color-think)' : 'var(--color-line-strong)'}
          />
        </svg>
      ))}
    </span>
  )
}
