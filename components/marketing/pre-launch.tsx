import { Section, Eyebrow } from './section'

/**
 * Where social proof will go.
 *
 * Worth has no users, so it has no testimonials, no ratings and no savings
 * figures — and a wall of "Example testimonial" placeholders on a live page
 * reads as an unfinished template, which is worse than saying nothing.
 *
 * So this section says the true thing instead. It occupies the slot in the
 * page's rhythm that proof will occupy, and swapping in real quotes later is a
 * content change, not a layout one.
 */
export function PreLaunch() {
  return (
    <Section tone="sunk">
      <div className="mx-auto max-w-[46rem] text-center">
        <Eyebrow>
          <span className="mx-auto">Where the reviews go</span>
        </Eyebrow>

        <p className="text-statement text-ink mt-6 font-serif leading-[1.08] font-medium">
          No testimonials yet. Worth hasn’t launched.
        </p>

        <p className="text-lead text-graphite mx-auto mt-6 max-w-[46ch]">
          There are no user counts, star ratings or “saved our customers €2M” claims on this page,
          because none of them would be true. When Worth has saved someone real money, they can say
          so here themselves.
        </p>

        <p className="text-graphite mx-auto mt-5 max-w-[46ch] text-[0.9375rem] leading-relaxed">
          Until then the only evidence on offer is the product itself, which is why so much of this
          page is spent showing it.
        </p>
      </div>
    </Section>
  )
}
