import { Section, Eyebrow, Statement, Disclosure } from './section'
import { ProductImage } from '@/components/worth/product-image'

/**
 * Beat 01 — the moment before Worth.
 *
 * The product, at size, with the listing's numbers set against it as type
 * rather than as UI. Earlier this section drew a fake browser window around the
 * photograph; that chrome said nothing — Worth is not a Mac app, and a visitor
 * does not need a pretend address bar to recognise a shop.
 *
 * What is left is the situation itself: a thing you want, a price, a rating,
 * and no way to tell whether the price is fair. The section is deliberately
 * almost copy-free, so the turn in beat 02 lands.
 */
export function FoundSomething() {
  return (
    <Section tone="sunk">
      <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] lg:gap-16">
        <div className="order-2 lg:order-1">
          <Eyebrow index="01">You found something</Eyebrow>
          <Statement className="mt-5 max-w-[16ch]">You found something you want.</Statement>
          <p className="text-lead text-graphite mt-6 max-w-[38ch]">
            It looks right. The reviews look fine. The price looks… like a price.
          </p>

          {/* The listing's own facts, as type. */}
          <dl className="border-line mt-10 grid max-w-[30rem] grid-cols-3 gap-4 border-t pt-6">
            {[
              ['Price', '€399'],
              ['Rating', '4.4'],
              ['Ratings', '2,140'],
            ].map(([k, v]) => (
              <div key={k}>
                <dt className="label text-faint">{k}</dt>
                <dd className="tnum text-ink mt-2 text-[1.75rem] leading-none font-semibold tracking-[-0.035em]">
                  {v}
                </dd>
              </div>
            ))}
          </dl>
        </div>

        {/* The product itself, large and unframed. */}
        <div className="order-1 lg:order-2">
          <div className="relative">
            <ProductImage
              asset="headphones"
              sizes="(max-width: 1024px) 100vw, 560px"
              className="aspect-[4/3] w-full"
            />
            <p className="text-ink absolute bottom-4 left-4 max-w-[18ch] text-[0.9375rem] font-medium sm:bottom-6 sm:left-6 sm:text-[1.0625rem]">
              Over-ear noise-cancelling headphones
              <span className="text-graphite block text-[0.8125rem] font-normal">
                Audio Store · In stock
              </span>
            </p>
          </div>

          <Disclosure className="mt-4">
            Illustrative listing. Not a real product, price or seller.
          </Disclosure>
        </div>
      </div>
    </Section>
  )
}
