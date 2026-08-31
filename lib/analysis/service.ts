import 'server-only'

import { createClient } from '@/lib/supabase/server'
import { getEngine } from './engine'
import type {
  Analysis,
  AnalysisInput,
  AnalysisResult,
  AnalysisStatus,
  Category,
  InputType,
  PublicAnalysis,
  Signal,
  Verdict,
} from './types'
import type { Database } from '@/types/database'

/**
 * The analysis service — the only thing the UI calls.
 *
 * Components never touch the engine or the database directly. When the real
 * research engine replaces the fixture engine, this file is the only place that
 * needs to know.
 */

type Row = Database['public']['Tables']['analyses']['Row']

function toAnalysis(row: Row): Analysis {
  return {
    id: row.id,
    status: row.status as AnalysisStatus,
    inputType: row.input_type as InputType,
    inputUrl: row.input_url,
    category: row.category as Category | null,
    title: row.title,
    score: row.score,
    verdict: row.verdict as Verdict | null,
    summary: row.summary,
    currency: row.currency,
    priceMinor: row.price_minor,
    bestPriceMinor: row.best_price_minor,
    result: row.result as AnalysisResult | null,
    shareSlug: row.share_slug,
    sharedAt: row.shared_at,
    createdAt: row.created_at,
    completedAt: row.completed_at,
    errorMessage: row.error_message,
    isFixture: row.is_fixture,
  }
}

/**
 * Creates a pending analysis, then runs the engine.
 *
 * Row Level Security enforces ownership — the insert can only ever write a row
 * belonging to the calling user.
 */
export async function createAnalysis(
  userId: string,
  input: AnalysisInput,
): Promise<{ ok: true; id: string } | { ok: false; error: string }> {
  const supabase = await createClient()

  const { data, error } = await supabase
    .from('analyses')
    .insert({
      user_id: userId,
      input_type: input.type,
      input_url: input.type === 'url' ? input.url : null,
      input_storage_path: input.type === 'screenshot' ? input.storagePath : null,
      category: input.category,
      status: 'processing',
    })
    .select('id')
    .single()

  if (error || !data) {
    return { ok: false, error: 'Could not start that analysis. Please try again.' }
  }

  await runEngine(data.id, input)
  return { ok: true, id: data.id }
}

/** Runs the configured engine and writes the result back. */
async function runEngine(id: string, input: AnalysisInput): Promise<void> {
  const supabase = await createClient()
  const engine = getEngine()

  try {
    const output = await engine.analyze(input)
    await supabase
      .from('analyses')
      .update({
        status: 'complete',
        title: output.title,
        category: output.category,
        score: output.score,
        verdict: output.verdict,
        summary: output.summary,
        currency: output.currency,
        price_minor: output.priceMinor,
        best_price_minor: output.bestPriceMinor,
        result: output.result,
        engine: engine.name,
        is_fixture: output.isFixture,
        completed_at: new Date().toISOString(),
      })
      .eq('id', id)
  } catch {
    await supabase
      .from('analyses')
      .update({
        status: 'failed',
        error_message: 'Worth could not complete this analysis.',
        completed_at: new Date().toISOString(),
      })
      .eq('id', id)
  }
}

export async function getAnalysis(id: string): Promise<Analysis | null> {
  const supabase = await createClient()
  const { data } = await supabase.from('analyses').select('*').eq('id', id).maybeSingle()
  return data ? toAnalysis(data) : null
}

export async function listAnalyses(limit = 50): Promise<Analysis[]> {
  const supabase = await createClient()
  const { data } = await supabase
    .from('analyses')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(limit)
  return (data ?? []).map(toAnalysis)
}

export async function countAnalyses(): Promise<number> {
  const supabase = await createClient()
  const { count } = await supabase.from('analyses').select('id', { count: 'exact', head: true })
  return count ?? 0
}

/** Generates a share slug for an analysis the caller owns. */
export async function shareAnalysis(id: string): Promise<string | null> {
  const supabase = await createClient()

  const { data: existing } = await supabase
    .from('analyses')
    .select('share_slug, status')
    .eq('id', id)
    .maybeSingle()

  if (!existing || existing.status !== 'complete') return null
  if (existing.share_slug) return existing.share_slug

  const slug = crypto.randomUUID().replace(/-/g, '').slice(0, 12)
  const { error } = await supabase
    .from('analyses')
    .update({ share_slug: slug, shared_at: new Date().toISOString() })
    .eq('id', id)

  return error ? null : slug
}

/**
 * Reads a publicly shared analysis.
 *
 * Goes through a SECURITY DEFINER function that returns only the shareable
 * columns. There is deliberately no anonymous SELECT policy on `analyses` — a
 * public share must never be able to expose the submitted URL, the uploaded
 * screenshot or who ran the analysis.
 */
export async function getPublicAnalysis(slug: string): Promise<PublicAnalysis | null> {
  const supabase = await createClient()
  const { data, error } = await supabase.rpc('get_public_analysis', { slug })

  const row = Array.isArray(data) ? data[0] : null
  if (error || !row || row.score === null || row.verdict === null) return null

  return {
    shareSlug: row.share_slug,
    title: row.title,
    score: row.score,
    verdict: row.verdict as Verdict,
    summary: row.summary,
    currency: row.currency,
    priceMinor: row.price_minor,
    bestPriceMinor: row.best_price_minor,
    signals: (row.signals ?? []) as unknown as Signal[],
    isFixture: row.is_fixture,
  }
}
