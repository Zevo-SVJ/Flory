import type { AnalysisInput } from '../types'
import { verdictFromScore } from '../verdict'
import type { AnalysisEngine, EngineOutput } from './types'

/**
 * DEVELOPMENT FIXTURE ENGINE — NOT REAL ANALYSIS.
 *
 * This produces a structurally complete, deterministic analysis so the full
 * product experience (submit → progress → result → share) can be built and
 * tested before the research engine exists.
 *
 * It performs NO research. It does not fetch the URL, read reviews, compare
 * prices or look at the screenshot. Every output is derived from a hash of the
 * input string, which is why the same link always returns the same result.
 *
 * Everything it returns is flagged `isFixture: true`, which the UI renders as a
 * visible notice. Fixture output must never be presented to a user as real
 * research. See `lib/analysis/engine/index.ts` for how the engine is selected.
 */

/** FNV-1a. Deterministic, so a given input always yields the same example. */
function hash(input: string): number {
  let h = 0x811c9dc5
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i)
    h = Math.imul(h, 0x01000193) >>> 0
  }
  return h >>> 0
}

function pick<T>(items: readonly T[], seed: number): T {
  // Non-empty arrays only — every table below is a literal with entries.
  return items[seed % items.length] as T
}

const TITLES = [
  'Wireless noise-cancelling headphones',
  'Robot vacuum with mapping',
  '4K portable monitor',
  'Ergonomic mesh office chair',
  'Espresso machine with grinder',
  'Smart fitness tracker',
] as const

const SUMMARIES = {
  buy: [
    'The price is fair and buyers consistently report it lasts.',
    'You are paying about what this is worth, and the seller is solid.',
  ],
  think_twice: [
    'It is decent, but you are paying a premium for the name.',
    'Reviews are split on the one thing you are buying it for.',
  ],
  skip: [
    'You are paying too much for what you get.',
    'A comparable option costs meaningfully less.',
  ],
} as const

export class FixtureEngine implements AnalysisEngine {
  readonly name = 'fixture-v1'

  async analyze(input: AnalysisInput): Promise<EngineOutput> {
    const seed = hash(input.type === 'url' ? input.url : input.storagePath)

    // Spread scores across the full range so all three verdicts are reachable.
    const score = 12 + (seed % 78)
    const verdict = verdictFromScore(score)
    const priceMinor = (4900 + (seed % 240) * 100) as number
    // Below-par scores get a cheaper alternative; strong scores do not.
    const bestPriceMinor =
      verdict === 'buy' ? null : Math.round(priceMinor * (0.52 + ((seed >> 8) % 25) / 100))

    return {
      title: pick(TITLES, seed),
      category: input.category ?? 'product',
      score,
      verdict,
      summary: pick(SUMMARIES[verdict], seed >> 4),
      currency: 'EUR',
      priceMinor,
      bestPriceMinor,
      isFixture: true,
      result: {
        valueSummary:
          'Example value breakdown. The real engine will describe what you actually get for the price.',
        signals: [
          {
            kind: 'price',
            tone: verdict === 'buy' ? 'positive' : 'negative',
            label: 'Price',
            detail:
              verdict === 'buy'
                ? 'Sits at the low end of the typical range for this spec.'
                : 'Above the typical range for comparable options.',
          },
          {
            kind: 'reviews',
            tone: verdict === 'skip' ? 'negative' : 'caution',
            label: 'Reviews',
            detail: 'Buyers repeatedly mention the same weak point.',
          },
          {
            kind: 'trust',
            tone: 'neutral',
            label: 'Trust',
            detail: 'Seller has a normal returns policy and a trading history.',
          },
          {
            kind: 'value',
            tone: verdict === 'buy' ? 'positive' : 'caution',
            label: 'Value',
            detail: 'Specification is mid-range for this price band.',
          },
          {
            kind: 'risk',
            tone: verdict === 'skip' ? 'caution' : 'neutral',
            label: 'Risk',
            detail: 'No significant warning signs found.',
          },
          {
            kind: 'alternative',
            tone: bestPriceMinor ? 'positive' : 'neutral',
            label: 'Alternatives',
            detail: bestPriceMinor
              ? 'A comparable option was found for less.'
              : 'Nothing clearly better at this price.',
          },
        ],
        evidence: [
          {
            id: 'e1',
            kind: 'price',
            claim: 'Example evidence line. The real engine will cite a source for every claim.',
            source: { label: 'Fixture data — not a real source' },
          },
          {
            id: 'e2',
            kind: 'reviews',
            claim: 'Example review pattern. Real analysis will quote recurring buyer reports.',
            source: { label: 'Fixture data — not a real source' },
          },
        ],
        alternatives: bestPriceMinor
          ? [
              {
                id: 'a1',
                title: 'Comparable option',
                priceMinor: bestPriceMinor,
                currency: 'EUR',
                reason: 'Example alternative. Real analysis will explain the trade-off.',
              },
            ]
          : [],
      },
    }
  }
}
