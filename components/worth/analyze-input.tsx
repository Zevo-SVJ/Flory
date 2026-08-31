'use client'

import Link from 'next/link'
import { useId, useState } from 'react'
import { useRouter } from 'next/navigation'
import { validateUrl } from '@/lib/analysis/validate'
import { cn } from '@/lib/utils/cn'

/**
 * The Worth field — the product's primary object.
 *
 * Built as one continuous surface with the action fused to it, so it reads as
 * a search-and-investigate instrument rather than a form input with a button
 * underneath. That fusion holds on mobile too: the button sits inside the
 * field rather than becoming a full-width bar, which is what made the previous
 * version look like every other SaaS page.
 *
 * It remains a real <form> that GETs to /analyze, so it works before
 * hydration and without JavaScript.
 */
export function AnalyzeInput({
  defaultValue = '',
  size = 'lg',
  showScreenshot = true,
  className,
}: {
  defaultValue?: string
  size?: 'md' | 'lg'
  showScreenshot?: boolean
  className?: string
}) {
  const id = useId()
  const router = useRouter()
  const [value, setValue] = useState(defaultValue)
  const [error, setError] = useState<string | null>(null)
  const [focused, setFocused] = useState(false)
  const [pending, setPending] = useState(false)

  const tall = size === 'lg'

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
      <form action="/analyze" method="get" onSubmit={handleSubmit}>
        <label htmlFor={id} className="sr-only">
          Paste a product, offer or URL to analyse
        </label>

        <div
          className={cn(
            'rounded-input bg-surface flex items-center gap-2 border transition-all duration-200',
            'motion-reduce:transition-none',
            tall ? 'h-15 pr-1.5 pl-4 sm:h-17 sm:pr-2 sm:pl-5' : 'h-14 pr-1.5 pl-4 sm:pl-4',
            error
              ? 'border-skip shadow-none'
              : focused
                ? 'border-worth shadow-[0_0_0_4px_var(--color-worth-wash)]'
                : 'border-line-strong shadow-object',
          )}
        >
          <LinkGlyph active={focused || value.length > 0} className="hidden sm:block" />

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
            value={value}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            onChange={(event) => {
              setValue(event.target.value)
              if (error) setError(null)
            }}
            placeholder="Paste a product, offer or URL…"
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? `${id}-error` : undefined}
            className={cn(
              'text-ink h-full min-w-0 flex-1 self-stretch bg-transparent outline-none',
              'placeholder:text-faint',
              tall && 'sm:text-[1.0625rem]',
            )}
          />

          <button
            type="submit"
            disabled={pending}
            className={cn(
              'bg-worth inline-flex shrink-0 items-center justify-center rounded-[0.5rem] font-medium text-white',
              'hover:bg-worth-deep transition-colors disabled:opacity-60',
              'motion-reduce:transition-none',
              tall
                ? 'h-12 px-3.5 text-[0.9375rem] sm:h-13 sm:px-6 sm:text-base'
                : 'h-11 px-3.5 text-[0.9375rem]',
            )}
          >
            {pending ? 'Checking…' : 'Analyze'}
          </button>
        </div>

        {error && (
          <p id={`${id}-error`} role="alert" className="text-skip mt-2.5 text-sm font-medium">
            {error}
          </p>
        )}
      </form>

      {showScreenshot && (
        <p className="text-graphite mt-3 text-[0.8125rem]">
          No link?{' '}
          <Link
            href="/analyze?input=screenshot"
            className="text-worth decoration-worth-line hover:decoration-worth font-medium underline underline-offset-4 transition-colors motion-reduce:transition-none"
          >
            Upload a screenshot
          </Link>{' '}
          instead.
        </p>
      )}
    </div>
  )
}

/** Link glyph. Turns Worth Blue once the field is live. */
function LinkGlyph({ active, className }: { active: boolean; className?: string }) {
  return (
    <svg
      width="19"
      height="19"
      viewBox="0 0 20 20"
      fill="none"
      aria-hidden
      className={cn(
        'shrink-0 transition-colors motion-reduce:transition-none',
        active ? 'text-worth' : 'text-faint',
        className,
      )}
    >
      <path
        d="M8.2 11.8a3.4 3.4 0 0 0 5.1.4l2.3-2.3a3.4 3.4 0 0 0-4.8-4.8l-1.3 1.3M11.8 8.2a3.4 3.4 0 0 0-5.1-.4l-2.3 2.3a3.4 3.4 0 0 0 4.8 4.8l1.3-1.3"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
