import { FixtureEngine } from './fixture'
import type { AnalysisEngine } from './types'

export type { AnalysisEngine, EngineOutput } from './types'

/**
 * Engine selection — the single place the real research engine gets connected.
 *
 * To ship real analysis:
 *   1. Implement `AnalysisEngine` in `lib/analysis/engine/research.ts`.
 *   2. Return it from here.
 *
 * Nothing else in the application changes. The database schema, the service
 * layer, the result page, the share card and the history list are all already
 * written against `EngineOutput`.
 */
export function getEngine(): AnalysisEngine {
  return new FixtureEngine()
}

/**
 * Whether Worth is currently running on fixture data rather than real research.
 * Drives the visible notice shown on every result — see `<FixtureNotice />`.
 */
export function isUsingFixtureEngine(): boolean {
  return getEngine().name.startsWith('fixture')
}
