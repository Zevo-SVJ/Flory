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
 * twice on a genuinely good product, because of the price" demonstrates the
 * product's actual point far better than a generic low score does.
 *
 * The example product is deliberately unbranded. Publishing an evaluative
 * verdict with invented prices against a real, named commercial product would
 * be a fabricated review of someone's actual product, however clearly the page
 * labels it — so the illustration keeps the shape and drops the brand.
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
  category: 'product',
  title: 'Over-ear noise-cancelling headphones',
  score: 61,
  verdict: 'think_twice',
  summary: 'The headphones are good. The price isn’t.',
  priceMinor: 39900,
  bestPriceMinor: 32900,
  result: {
    valueSummary:
      'Class-leading noise cancelling and a 30-hour battery. Nothing wrong with the product — three other retailers are simply selling the same model for less.',
    signals: [
      {
        kind: 'price',
        tone: 'negative',
        label: 'Price',
        detail: '€70 above the best price found for the same model.',
      },
      {
        kind: 'reviews',
        tone: 'positive',
        label: 'Reviews',
        detail: 'Battery life and call quality are consistently praised.',
      },
      {
        kind: 'trust',
        tone: 'positive',
        label: 'Trust',
        detail: 'Authorised seller, 30-day returns, 2-year warranty.',
      },
      {
        kind: 'value',
        tone: 'positive',
        label: 'Value',
        detail: 'Top of its class for noise cancelling at this tier.',
      },
      {
        kind: 'risk',
        tone: 'caution',
        label: 'Risk',
        detail: 'A refresh is expected within about six months.',
      },
      {
        kind: 'alternative',
        tone: 'positive',
        label: 'Alternatives',
        detail: 'Identical model, authorised retailer, €329.',
      },
    ],
    evidence: [
      {
        id: 'p1',
        kind: 'price',
        claim: 'Listed at €399 while three other authorised retailers carry it at €329–€349.',
        source: { label: 'Illustrative example — not a real source' },
      },
      {
        id: 'p2',
        kind: 'reviews',
        claim: '“Battery life is genuinely 30 hours” appears across long-term reviews.',
        source: { label: 'Illustrative example — not a real source' },
      },
      {
        id: 'p3',
        kind: 'risk',
        claim: 'The previous two generations were replaced on an 18-month cycle.',
        source: { label: 'Illustrative example — not a real source' },
      },
    ],
    alternatives: [
      {
        id: 'p-alt-1',
        title: 'Same model, authorised retailer',
        priceMinor: 32900,
        currency: 'EUR',
        reason: 'Identical product and warranty, €70 less.',
      },
    ],
  },
}

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
    id: 'physical',
    kind: 'Physical product',
    title: 'Over-ear noise-cancelling headphones',
    meta: 'Over-ear headphones',
    price: '€399',
    bestPrice: '€329',
    score: 61,
    verdict: 'think_twice',
    line: 'Good product, wrong price. Same model for €329.',
  },
  {
    id: 'software',
    kind: 'Software',
    title: 'Project tool, annual plan',
    meta: 'Team subscription',
    price: '€96/yr',
    bestPrice: null,
    score: 82,
    verdict: 'buy',
    line: 'Priced fairly for what you use, and easy to leave.',
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

/* The evidence wall: real-shaped fragments from the primary investigation. */
export const EVIDENCE_WALL = {
  priceFound: '€329',
  priceListed: '€399',
  retailersChecked: 11,
  reviewPositive: '“Battery life is genuinely 30 hours.”',
  reviewNegative: '“The case is bulkier than the last generation.”',
  reviewsRead: 2140,
  sellerReturns: '30-day returns',
  sellerWarranty: '2-year warranty',
  riskNote: 'A refresh is expected within about six months.',
}
