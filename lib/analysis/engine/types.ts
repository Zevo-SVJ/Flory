import type { Analysis, AnalysisInput, AnalysisResult, Category, Verdict } from '../types'

/**
 * What an analysis engine must produce.
 *
 * The real engine will run the full pipeline — identify, extract, research,
 * price analysis, review analysis, trust analysis, risk analysis, alternatives,
 * scoring, verdict generation — and return this shape. Everything above it (the
 * database, the service layer, every component) is already written against this
 * contract, so connecting the real engine is an implementation swap and nothing
 * more.
 */
export interface EngineOutput {
  title: string
  category: Category
  score: number
  verdict: Verdict
  summary: string
  currency: string
  priceMinor: number | null
  bestPriceMinor: number | null
  result: AnalysisResult
  /**
   * Whether this output came from real research. The fixture engine sets this
   * to true; the real engine will set it to false. It is persisted and surfaced
   * in the UI so fixture output can never be mistaken for real analysis.
   */
  isFixture: boolean
}

export interface AnalysisEngine {
  /** Stable identifier, recorded so results can be traced to their producer. */
  readonly name: string
  analyze(input: AnalysisInput): Promise<EngineOutput>
}

/** The engine's view of an analysis in progress. */
export type PendingAnalysis = Pick<Analysis, 'id' | 'inputType' | 'inputUrl' | 'category'>
