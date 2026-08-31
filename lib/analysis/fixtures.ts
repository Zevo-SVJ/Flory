import type { Analysis } from './types'

/**
 * Static examples used on the landing page.
 *
 * These are illustrative product previews, not real analyses, and every surface
 * that renders them labels them as such. The numbers come from the product
 * brief and describe a hypothetical purchase.
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

/** Hero preview and the verdict section. */
export const HERO_EXAMPLE: Analysis = {
  ...BASE,
  id: 'example-hero',
  category: 'product',
  title: 'Wireless noise-cancelling headphones',
  score: 34,
  verdict: 'skip',
  summary: 'You’re paying too much for what you get.',
  priceMinor: 17900,
  bestPriceMinor: 7900,
  result: {
    valueSummary:
      'Mid-range drivers and plastic hinges, priced alongside models with metal frames and better noise cancelling.',
    signals: [
      {
        kind: 'price',
        tone: 'negative',
        label: 'Price',
        detail: '€100 above comparable models with the same specification.',
      },
      {
        kind: 'reviews',
        tone: 'negative',
        label: 'Review concerns',
        detail: 'Buyers repeatedly report the hinge cracking within a year.',
      },
      {
        kind: 'trust',
        tone: 'neutral',
        label: 'Trust',
        detail: 'Established seller, standard 30-day returns.',
      },
      {
        kind: 'alternative',
        tone: 'positive',
        label: 'Alternative found',
        detail: 'A comparable model with a metal frame costs €79.',
      },
    ],
    evidence: [
      {
        id: 'ex-1',
        kind: 'price',
        claim:
          'Listed at €179 while four other retailers carry the same model between €99 and €129.',
        source: { label: 'Illustrative example — not a real source' },
      },
      {
        id: 'ex-2',
        kind: 'reviews',
        claim: 'Hinge failure is the most common complaint across long-term reviews.',
        source: { label: 'Illustrative example — not a real source' },
      },
      {
        id: 'ex-3',
        kind: 'value',
        claim: 'Noise cancelling measured a tier below models at the same price.',
        source: { label: 'Illustrative example — not a real source' },
      },
    ],
    alternatives: [
      {
        id: 'ex-alt-1',
        title: 'Comparable model, metal frame',
        priceMinor: 7900,
        currency: 'EUR',
        reason: 'Same noise cancelling tier, sturdier build, €100 less.',
      },
    ],
  },
}

/** The money section and the share card tell one consistent story. */
export const SHARE_EXAMPLE: Analysis = {
  ...BASE,
  id: 'example-share',
  category: 'product',
  title: 'Robot vacuum with mapping',
  score: 31,
  verdict: 'skip',
  summary: 'Worth found a comparable option for €159.',
  priceMinor: 24900,
  bestPriceMinor: 15900,
  result: {
    valueSummary: 'Same suction and mapping as models costing a third less.',
    signals: [
      {
        kind: 'price',
        tone: 'negative',
        label: 'Price',
        detail: '€90 above a comparable model.',
      },
      {
        kind: 'alternative',
        tone: 'positive',
        label: 'Alternative found',
        detail: 'Same suction and mapping for €159.',
      },
    ],
    evidence: [],
    alternatives: [],
  },
}
