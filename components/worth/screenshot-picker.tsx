'use client'

import Link from 'next/link'
import { cn } from '@/lib/utils/cn'

/**
 * Landing-page affordance for the screenshot input.
 *
 * Deliberately subordinate to Analyze — the hero has exactly one dominant
 * action. Uploading requires an account (the file is stored in a private
 * per-user folder), so this routes through the same auth flow as a URL.
 */
export function ScreenshotPicker({ className }: { className?: string }) {
  return (
    <p className={cn('text-muted text-center text-[0.8125rem] sm:text-left', className)}>
      <Link
        href="/analyze?input=screenshot"
        className="rounded-chip decoration-rule-strong hover:text-ink hover:decoration-ink inline-flex min-h-11 items-center gap-1.5 px-1 underline underline-offset-4 transition motion-reduce:transition-none"
      >
        <UploadIcon />
        Or upload a screenshot
      </Link>
    </p>
  )
}

function UploadIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M8 10.5V2m0 0L5 5m3-3 3 3M2.5 11v1.5A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V11"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
