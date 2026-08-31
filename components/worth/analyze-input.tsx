'use client'

import { useId, useState } from 'react'
import { useRouter } from 'next/navigation'
import { validateUrl } from '@/lib/analysis/validate'
import { cn } from '@/lib/utils/cn'
import { ScreenshotPicker } from './screenshot-picker'

/**
 * The primary product interaction.
 *
 * This is a real <form> that GETs to /analyze, so it works before hydration and
 * without JavaScript. The client layer only adds inline validation and the
 * screenshot affordance.
 *
 * If the visitor is signed out, /analyze redirects them to sign-up carrying the
 * URL — they never paste it twice. See `lib/auth/pending-input.ts`.
 */
export function AnalyzeInput({
  defaultValue = '',
  autoFocus = false,
  size = 'lg',
  showScreenshot = true,
  className,
}: {
  defaultValue?: string
  autoFocus?: boolean
  size?: 'md' | 'lg'
  showScreenshot?: boolean
  className?: string
}) {
  const id = useId()
  const router = useRouter()
  const [value, setValue] = useState(defaultValue)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  const height = size === 'lg' ? 'h-13 sm:h-15' : 'h-12 sm:h-13'

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const result = validateUrl(value)
    if (!result.ok) {
      setError(result.error)
      return
    }
    setError(null)
    setPending(true)
    router.push(`/analyze?url=${encodeURIComponent(result.url)}`)
  }

  return (
    <div className={cn('w-full', className)}>
      <form action="/analyze" method="get" onSubmit={handleSubmit} className="w-full">
        <label htmlFor={id} className="sr-only">
          Paste a product, offer or URL to analyse
        </label>

        <div className="flex flex-col gap-2 sm:relative sm:block">
          <input
            id={id}
            name="url"
            type="text"
            inputMode="url"
            autoComplete="url"
            enterKeyHint="go"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            autoFocus={autoFocus}
            value={value}
            onChange={(event) => {
              setValue(event.target.value)
              if (error) setError(null)
            }}
            placeholder="Paste a product, offer or URL…"
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? `${id}-error` : undefined}
            className={cn(
              'rounded-input bg-surface text-ink shadow-card w-full border px-4',
              'placeholder:text-faint',
              'focus:ring-ink/8 transition duration-200 focus:ring-4 focus:outline-none',
              'motion-reduce:transition-none',
              height,
              size === 'lg' ? 'sm:pr-36 sm:text-[1.0625rem]' : 'sm:pr-32',
              error ? 'border-skip focus:border-skip' : 'border-rule-strong focus:border-ink',
            )}
          />

          <button
            type="submit"
            disabled={pending}
            className={cn(
              'rounded-input bg-ink text-paper inline-flex w-full items-center justify-center font-medium',
              'hover:bg-ink-2 transition active:scale-[0.99] disabled:opacity-60',
              'motion-reduce:transition-none motion-reduce:active:scale-100',
              'sm:absolute sm:top-1.5 sm:right-1.5 sm:bottom-1.5 sm:w-auto sm:px-6',
              size === 'lg' ? 'h-12 text-base' : 'h-11 text-[0.9375rem]',
            )}
          >
            {pending ? 'Analysing…' : 'Analyze'}
          </button>
        </div>

        {error && (
          <p id={`${id}-error`} role="alert" className="text-skip mt-2 text-sm font-medium">
            {error}
          </p>
        )}
      </form>

      {showScreenshot && <ScreenshotPicker className="mt-3" />}
    </div>
  )
}
