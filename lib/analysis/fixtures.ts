import type { Analysis, Verdict } from './types'

/**
 * Illustrative examples used on the landing page.
 *
 * These are not real analyses. Worth's research engine isn't connected, and no
 * figure here describes a real listing, price or review — every surface that
 * renders them says so.
 *
 * They are written to be *plausible* rather than random, because the landing
 * page's job is to show what a Worth result looks like. A verdict of "think
 * twice on something that looked fine, because the real cost is higher than
 * the advertised one" demonstrates the product's actual point far better than
 * a generic low score does.
 *
 * The example is an online checkout rather than a named product. Two reasons:
 * the decision Worth is about is the moment before you pay, not any particular
 * object; and publishing an evaluative verdict with invented prices against a
 * real, named commercial product would be a fabricated review of someone's
 * actual product, however clearly the page labels it.
 */

const BASE = {
  status: 'complete',
  inputType: 'url',
  inputUrl: null,
  currency: 'EUR',
  shareSlug: null,
  sharedAt: null,
  createdAt: '2026-01-01T00:00:00.000Z',
  completedAt: '2026-01-01T00:00:00.000Z',
  errorMessage: null,
  isFixture: true,
} as const

/**
 * The primary example, used in the hero, the verdict moment, the money
 * section and the share card — one product followed all the way through, so
 * the page reads as a single investigation rather than six unrelated demos.
 */
export const PRIMARY_EXAMPLE: Analysis = {
  ...BASE,
  id: 'example-primary',
  category: 'software',
  title: 'Annual plan, paid upfront',
  score: 68,
  verdict: 'think_twice',
  summary: 'The deal looks good at first. The actual cost changes the picture.',
  priceMinor: 100700,
  bestPriceMinor: 72400,
  result: {
    valueSummary:
      'Nothing wrong with the service. The advertised €892 becomes €1,007 once the platform fee and the onboarding add-on are counted, and an equivalent plan is available monthly at €724 a year with better terms.',
    signals: [
      {
        kind: 'price',
        tone: 'caution',
        label: 'Price',
        detail: 'Advertised at €892. €1,007 is what actually leaves your account.',
      },
      {
        kind: 'fees',
        tone: 'negative',
        label: 'Fees',
        detail: '€84 platform fee and a €31 onboarding add-on, both added at checkout.',
      },
      {
        kind: 'reviews',
        tone: 'positive',
        label: 'Reviews',
        detail: 'Rated 4.5. Support response times are consistently praised.',
      },
      {
        kind: 'trust',
        tone: 'positive',
        label: 'Trust',
        detail: 'Established seller, clear terms, refunds honoured within 14 days.',
      },
      {
        kind: 'risk',
        tone: 'negative',
        label: 'Risk',
        detail: 'Annual billing locks you in. No refund after the first 14 days.',
      },
      {
        kind: 'alternative',
        tone: 'positive',
        label: 'Alternatives',
        detail: 'Equivalent plan, monthly, cancel any time — €724 a year.',
      },
    ],
    evidence: [
      {
        id: 'p1',
        kind: 'fees',
        claim: 'The €84 platform fee and €31 add-on appear only on the final checkout step.',
        source: { label: 'Illustrative example — not a real source' },
      },
      {
        id: 'p2',
        kind: 'reviews',
        claim: '“Support answered in under an hour” recurs across long-term reviews.',
        source: { label: 'Illustrative example — not a real source' },
      },
      {
        id: 'p3',
        kind: 'risk',
        claim: 'Annual plans are non-refundable after 14 days under the published terms.',
        source: { label: 'Illustrative example — not a real source' },
      },
    ],
    alternatives: [
      {
        id: 'p-alt-1',
        title: 'Equivalent plan, monthly billing',
        priceMinor: 72400,
        currency: 'EUR',
        reason: 'Same capability, cancel any time, €283 less over a year.',
      },
    ],
  },
}

/**
 * The money story, as the landing page tells it: what you think you are
 * paying, what you actually pay, and what Worth found instead.
 */
export const MONEY_EXAMPLE = {
  base: { label: 'Advertised', amount: '€892' },
  additions: [
    { label: 'Platform fee', amount: '€84' },
    { label: 'Onboarding add-on', amount: '€31' },
  ],
  actual: { label: 'What actually leaves your account', amount: '€1,007' },
  better: { label: 'Worth found', amount: '€724' },
  saving: '€283',
} as const

/**
 * The comparison: the option you found against the one Worth found. Same three
 * attributes on both sides, so the difference is legible at a glance.
 */
export const COMPARISON_EXAMPLE = {
  found: {
    heading: 'What you found',
    price: '€1,007',
    rows: [
      ['Rating', '4.5'],
      ['Billing', 'Annual, upfront'],
      ['Cancellation', '14 days, then locked in'],
    ],
  },
  worth: {
    heading: 'What Worth found',
    price: '€724',
    rows: [
      ['Rating', '4.7'],
      ['Billing', 'Monthly'],
      ['Cancellation', 'Any time'],
    ],
  },
  saving: '€283',
} as const

/* ------------------------------------------------------------------------ */
/* Worth works wherever money is about to be spent — not just retail.        */
/* ------------------------------------------------------------------------ */

export interface CategoryExample {
  id: string
  kind: string
  title: string
  meta: string
  price: string
  bestPrice: string | null
  score: number
  verdict: Verdict
  line: string
}

export const CATEGORY_EXAMPLES: CategoryExample[] = [
  {
    id: 'subscription',
    kind: 'Subscription',
    title: 'Annual plan, paid upfront',
    meta: 'Checkout, fees added at the last step',
    price: '€1,007',
    bestPrice: '€724',
    score: 68,
    verdict: 'think_twice',
    line: 'Fine service. The advertised price isn’t the price.',
  },
  {
    id: 'software',
    kind: 'Software',
    title: 'Design tool, team seats',
    meta: 'Per seat, billed yearly',
    price: '€96/yr',
    bestPrice: null,
    score: 82,
    verdict: 'buy',
    line: 'Priced fairly for the seats you use, and easy to leave.',
  },
  {
    id: 'course',
    kind: 'Digital product',
    title: '“Six-figure freelancing” course',
    meta: 'Online course, 14 modules',
    price: '€249',
    bestPrice: null,
    score: 28,
    verdict: 'skip',
    line: 'Outcome claims aren’t backed by anything checkable.',
  },
]

/* The research a person would otherwise do themselves: the fragments that end
   up spread across fifteen tabs before any decision gets made. */
export const RESEARCH_FRAGMENTS = [
  { text: '€892', sub: 'advertised' },
  { text: '4.5 ★', sub: '1,284 reviews' },
  { text: '“fees at checkout”', sub: 'review, 2025' },
  { text: '€84', sub: 'platform fee' },
  { text: 'Annual only', sub: 'billing terms' },
  { text: '€31', sub: 'onboarding add-on' },
  { text: '14 days', sub: 'refund window' },
  { text: '€724', sub: 'another provider' },
  { text: '4.7 ★', sub: '860 reviews' },
  { text: '“cancel any time”', sub: 'competitor terms' },
] as const
