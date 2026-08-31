'use client'

import Link from 'next/link'

export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="flex min-h-dvh items-center justify-center px-4">
      <div className="max-w-md text-center">
        <h1 className="text-title text-ink font-serif font-medium">Something broke.</h1>
        <p className="text-lead text-muted mt-3">
          That wasn’t meant to happen. Try again, and if it keeps happening, start over from the
          home page.
        </p>
        <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
          <button
            type="button"
            onClick={reset}
            className="rounded-input bg-ink text-paper inline-flex min-h-12 items-center justify-center px-6 font-medium"
          >
            Try again
          </button>
          <Link
            href="/"
            className="rounded-input border-rule-strong text-ink inline-flex min-h-12 items-center justify-center border px-6 font-medium"
          >
            Go to Worth
          </Link>
        </div>
      </div>
    </div>
  )
}
