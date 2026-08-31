import Link from 'next/link'
import { Wordmark } from '@/components/marketing/wordmark'
import { Card } from '@/components/ui/card'

/**
 * Shown when Supabase credentials are missing.
 *
 * Accounts, saved analyses and history all live in Supabase, so the app cannot
 * work without it. Saying so plainly beats a stack trace or a silent redirect
 * loop.
 */
export function SetupNotice() {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="pt-safe px-4 py-5 sm:px-6">
        <Link href="/" className="rounded-chip inline-flex" aria-label="Worth — home">
          <Wordmark />
        </Link>
      </header>
      <main className="flex flex-1 items-center justify-center px-4 pb-16 sm:px-6">
        <Card className="max-w-md p-6">
          <h1 className="text-heading text-ink font-serif font-medium">
            Worth isn’t connected yet.
          </h1>
          <p className="text-muted mt-3 text-[0.9375rem] leading-relaxed">
            Accounts and saved analyses need a Supabase project. Add{' '}
            <code className="bg-paper-sunk rounded px-1.5 py-0.5 text-[0.8125rem]">
              NEXT_PUBLIC_SUPABASE_URL
            </code>{' '}
            and{' '}
            <code className="bg-paper-sunk rounded px-1.5 py-0.5 text-[0.8125rem]">
              NEXT_PUBLIC_SUPABASE_ANON_KEY
            </code>{' '}
            to{' '}
            <code className="bg-paper-sunk rounded px-1.5 py-0.5 text-[0.8125rem]">.env.local</code>
            , then run the migrations in{' '}
            <code className="bg-paper-sunk rounded px-1.5 py-0.5 text-[0.8125rem]">
              supabase/migrations/
            </code>
            . See the README.
          </p>
          <Link
            href="/"
            className="text-ink mt-5 inline-flex min-h-11 items-center text-[0.9375rem] font-medium underline underline-offset-4"
          >
            Back to the landing page
          </Link>
        </Card>
      </main>
    </div>
  )
}
