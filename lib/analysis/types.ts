/**
 * The Worth analysis domain.
 *
 * These types are the contract between the UI and whatever produces an
 * analysis. The landing page's example card, the authenticated result page and
 * the public share page all render the SAME components against these types —
 * only the source of the data differs (fixtures today, the real research engine
 * next). Nothing in the UI needs to change when the engine lands.
 *
 * No AI, research or scraping logic ever belongs in this file or in a React
 * component. See `lib/analysis/engine/` for the boundary.
 */

export type Verdict = 'buy' | 'think_twice' | 'skip'

export type AnalysisStatus = 'pending' | 'processing' | 'complete' | 'failed'

export type InputType = 'url' | 'screenshot' | 'text'

export type Category = 'product' | 'software' | 'course' | 'other'

/** The six dimensions Worth reasons about. */
/* 'fees' is its own dimension rather than part of 'price': the gap between an
   advertised figure and the figure that actually leaves your account is the
   single thing Worth most often has to point at. */
export type SignalKind = 'price' | 'fees' | 'value' | 'reviews' | 'trust' | 'risk' | 'alternative'

/** How a signal reflects on the purchase. Drives the verdict colour. */
export type SignalTone = 'positive' | 'caution' | 'negative' | 'neutral'

export interface Signal {
  kind: SignalKind
  tone: SignalTone
  /** Short label, e.g. "Price". */
  label: string
  /** One concrete sentence, e.g. "€100 above the typical price for this spec." */
  detail: string
}

/**
 * A single supporting fact. Every claim Worth makes should eventually be
 * traceable to a source — the engine is responsible for populating `source`.
 */
export interface Evidence {
  id: string
  kind: SignalKind
  claim: string
  source: {
    label: string
    url?: string
  }
}

export interface Alternative {
  id: string
  title: string
  priceMinor: number | null
  currency: string
  /** Why this is worth considering instead. */
  reason: string
  url?: string
}

/** The structured payload persisted in `analyses.result`. */
export interface AnalysisResult {
  signals: Signal[]
  evidence: Evidence[]
  alternatives: Alternative[]
  /** What the buyer actually gets for the money. */
  valueSummary: string | null
}

export interface Analysis {
  id: string
  status: AnalysisStatus
  inputType: InputType
  inputUrl: string | null
  category: Category | null
  title: string | null

  score: number | null
  verdict: Verdict | null
  /** One highly understandable sentence. The verdict's reason. */
  summary: string | null

  /** ISO 4217 code. Money is always stored in integer minor units. */
  currency: string
  priceMinor: number | null
  bestPriceMinor: number | null

  result: AnalysisResult | null

  shareSlug: string | null
  sharedAt: string | null

  createdAt: string
  completedAt: string | null
  errorMessage: string | null

  /**
   * True when this analysis came from the development fixture engine rather
   * than real research. The UI MUST surface this to the user — see
   * `<FixtureNotice />`. Never present fixture output as real analysis.
   */
  isFixture: boolean
}

/**
 * The restricted representation exposed on public share pages.
 *
 * Deliberately omits everything private: the owner, the submitted URL, the
 * uploaded screenshot path and the raw evidence sources. A public share must
 * never be able to reveal what someone was shopping for beyond the verdict
 * they chose to publish.
 */
export interface PublicAnalysis {
  shareSlug: string
  title: string | null
  score: number
  verdict: Verdict
  summary: string | null
  currency: string
  priceMinor: number | null
  bestPriceMinor: number | null
  signals: Signal[]
  isFixture: boolean
}

/** What the user submits. Validated before it reaches the engine. */
export type AnalysisInput =
  | { type: 'url'; url: string; category: Category | null }
  | { type: 'screenshot'; storagePath: string; category: Category | null }
