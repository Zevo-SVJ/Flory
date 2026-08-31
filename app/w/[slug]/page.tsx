import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { getPublicAnalysis } from '@/lib/analysis/service'
import { isSupabaseConfigured, siteUrl } from '@/lib/supabase/env'
import { ShareCard } from '@/components/worth/share-card'
import { SignalList } from '@/components/worth/signal-list'
import { AnalyzeInput } from '@/components/worth/analyze-input'
import { FixtureNotice } from '@/components/worth/fixture-notice'
import { SiteNav } from '@/components/marketing/site-nav'
import { SiteFooter } from '@/components/marketing/site-footer'
import { VERDICT_LABEL } from '@/lib/analysis/verdict'

/**
 * A publicly shared verdict.
 *
 * Reads through `get_public_analysis()`, which returns the verdict, the money
 * and the signals only. There is no anonymous SELECT policy on `analyses`, so
 * the analysed URL, the uploaded screenshot, the evidence sources and the owner
 * are unreachable from here by construction.
 *
 * This is the top of the loop: whoever lands here can immediately check
 * something of their own.
 */
export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>
}): Promise<Metadata> {
  if (!isSupabaseConfigured()) return { title: 'Shared verdict' }

  const { slug } = await params
  const analysis = await getPublicAnalysis(slug)
  if (!analysis) return { title: 'Verdict not found' }

  const title = `${analysis.score}/100 — ${VERDICT_LABEL[analysis.verdict]}`
  const description = analysis.summary ?? 'A Worth verdict.'

  return {
    title,
    description,
    alternates: { canonical: `${siteUrl()}/w/${slug}` },
    openGraph: { title: `${title} · Worth`, description, type: 'article' },
    twitter: { card: 'summary_large_image', title: `${title} · Worth`, description },
  }
}

export default async function SharePage({ params }: { params: Promise<{ slug: string }> }) {
  if (!isSupabaseConfigured()) notFound()

  const { slug } = await params
  const analysis = await getPublicAnalysis(slug)
  if (!analysis) notFound()

  return (
    <div className="flex min-h-dvh flex-col">
      <SiteNav />
      <main className="flex-1">
        <div className="mx-auto max-w-2xl px-4 py-10 sm:px-6 sm:py-16">
          <div className="mx-auto w-full max-w-[21rem]">
            <ShareCard
              score={analysis.score}
              verdict={analysis.verdict}
              title={analysis.title}
              summary={analysis.summary}
              priceMinor={analysis.priceMinor}
              bestPriceMinor={analysis.bestPriceMinor}
              currency={analysis.currency}
            />
          </div>

          {analysis.isFixture && <FixtureNotice className="mt-6" />}

          {analysis.signals.length > 0 && (
            <div className="border-line mt-8 border-t pt-6">
              <h2 className="text-graphite text-[0.6875rem] font-medium tracking-[0.14em] uppercase">
                Why this verdict
              </h2>
              <div className="mt-3">
                <SignalList signals={analysis.signals} />
              </div>
            </div>
          )}

          <div className="border-line mt-10 border-t pt-8">
            <h2 className="text-heading text-ink font-serif font-medium">
              Thinking about buying something?
            </h2>
            <p className="text-graphite mt-2 text-[0.9375rem]">
              Paste it and Worth will tell you whether it’s worth your money.
            </p>
            <div className="mt-5">
              <AnalyzeInput size="md" showScreenshot={false} />
            </div>
          </div>
        </div>
      </main>
      <SiteFooter />
    </div>
  )
}
