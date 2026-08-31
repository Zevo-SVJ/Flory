'use client'

import { useState, useTransition } from 'react'
import type { Analysis } from '@/lib/analysis/types'
import { createShareLink } from '@/lib/analysis/actions'
import { ShareCard } from '@/components/worth/share-card'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

/**
 * Sharing a result.
 *
 * Creates a public link backed by a restricted representation: the share page
 * shows the verdict, the money and the signals, and nothing else. The URL that
 * was analysed, the uploaded screenshot and the owner never leave this account.
 */
export function ShareResult({ analysis }: { analysis: Analysis }) {
  const [slug, setSlug] = useState(analysis.shareSlug)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [pending, startTransition] = useTransition()

  if (analysis.score === null || analysis.verdict === null) return null

  const shareUrl = slug ? `${window.location.origin}/w/${slug}` : null

  function handleCreate() {
    setError(null)
    startTransition(async () => {
      const result = await createShareLink(analysis.id)
      if ('error' in result) setError(result.error)
      else setSlug(result.slug)
    })
  }

  async function handleCopy() {
    if (!shareUrl) return
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setError('Couldn’t copy. Select the link and copy it manually.')
    }
  }

  return (
    <Card className="flex flex-col gap-5 p-5">
      <div>
        <h2 className="text-graphite text-[0.6875rem] font-medium tracking-[0.14em] uppercase">
          Share this
        </h2>
        <p className="text-graphite mt-2 text-[0.9375rem] leading-snug">
          A shared result shows the verdict and the money — never the link you pasted.
        </p>
      </div>

      <div className="mx-auto w-full max-w-[17rem]">
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

      {shareUrl ? (
        <div className="flex flex-col gap-2">
          <div className="rounded-input border-line bg-paper-2 flex items-center gap-2 border px-3 py-2.5">
            <span className="text-ink min-w-0 flex-1 truncate text-[0.875rem]">{shareUrl}</span>
          </div>
          <Button type="button" onClick={handleCopy} variant="secondary">
            {copied ? 'Copied' : 'Copy link'}
          </Button>
        </div>
      ) : (
        <Button type="button" onClick={handleCreate} disabled={pending}>
          {pending ? 'Creating link…' : 'Create share link'}
        </Button>
      )}

      {error && (
        <p role="alert" className="text-skip text-[0.875rem] font-medium">
          {error}
        </p>
      )}
    </Card>
  )
}
