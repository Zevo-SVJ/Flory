'use client'

import { useState, useTransition } from 'react'
import { submitUrl, submitUrlForm } from '@/lib/analysis/actions'
import { validateUrl, CATEGORIES, CATEGORY_LABEL } from '@/lib/analysis/validate'
import type { Category } from '@/lib/analysis/types'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils/cn'
import { ScreenshotUpload } from './screenshot-upload'

/**
 * The full analyse form: URL, optional category, screenshot alternative.
 *
 * Submission goes through a server action, so it works without client-side
 * JavaScript; the client layer adds inline validation and the pending state.
 */
export function AnalyzeForm({
  defaultUrl,
  userId,
  openScreenshot,
  initialError,
}: {
  defaultUrl: string
  userId: string
  openScreenshot: boolean
  initialError?: string
}) {
  const [url, setUrl] = useState(defaultUrl)
  const [category, setCategory] = useState<Category | null>(null)
  const [error, setError] = useState<string | null>(initialError ?? null)
  const [pending, startTransition] = useTransition()

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    const check = validateUrl(url)
    if (!check.ok) {
      event.preventDefault()
      setError(check.error)
      return
    }
    setError(null)
    event.preventDefault()
    const data = new FormData()
    data.set('url', url)
    if (category) data.set('category', category)
    startTransition(async () => {
      const result = await submitUrl(data)
      if (result?.error) setError(result.error)
    })
  }

  return (
    <div className="flex flex-col gap-6">
      <form action={submitUrlForm} onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <label htmlFor="analyze-url" className="sr-only">
            Paste a product, offer or URL
          </label>
          <input
            id="analyze-url"
            name="url"
            type="text"
            inputMode="url"
            enterKeyHint="go"
            autoComplete="url"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            value={url}
            onChange={(event) => {
              setUrl(event.target.value)
              if (error) setError(null)
            }}
            placeholder="Paste a product, offer or URL…"
            aria-invalid={error ? true : undefined}
            className={cn(
              'rounded-input bg-surface text-ink shadow-card h-13 w-full border px-4',
              'placeholder:text-faint focus:ring-ink/8 transition focus:ring-4 focus:outline-none',
              'motion-reduce:transition-none',
              error ? 'border-skip' : 'border-rule-strong focus:border-ink',
            )}
          />
        </div>

        <fieldset className="flex flex-col gap-2">
          <legend className="text-muted text-[0.6875rem] font-medium tracking-[0.14em] uppercase">
            Category — optional
          </legend>
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map((value) => {
              const active = category === value
              return (
                <button
                  key={value}
                  type="button"
                  aria-pressed={active}
                  onClick={() => setCategory(active ? null : value)}
                  className={cn(
                    'rounded-chip min-h-11 border px-3.5 text-[0.875rem] transition motion-reduce:transition-none',
                    active
                      ? 'border-ink bg-ink text-paper'
                      : 'border-rule-strong bg-surface text-muted hover:border-ink hover:text-ink',
                  )}
                >
                  {CATEGORY_LABEL[value]}
                </button>
              )
            })}
          </div>
          {category && <input type="hidden" name="category" value={category} />}
        </fieldset>

        {error && (
          <p role="alert" className="text-skip text-[0.875rem] font-medium">
            {error}
          </p>
        )}

        <Button
          type="submit"
          size="lg"
          disabled={pending}
          className="w-full sm:w-auto sm:self-start sm:px-10"
        >
          {pending ? 'Analysing…' : 'Analyze'}
        </Button>
      </form>

      <div className="border-rule border-t pt-6">
        <ScreenshotUpload userId={userId} defaultOpen={openScreenshot} />
      </div>
    </div>
  )
}
