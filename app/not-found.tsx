import Link from 'next/link'
import { Wordmark } from '@/components/marketing/wordmark'

export default function NotFound() {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="pt-safe px-4 py-5 sm:px-6">
        <Link href="/" className="rounded-note inline-flex" aria-label="Worth — home">
          <Wordmark />
        </Link>
      </header>
      <main className="flex flex-1 items-center justify-center px-4 pb-20 sm:px-6">
        <div className="max-w-md text-center">
          <h1 className="text-statement text-ink font-serif font-medium">There’s nothing here.</h1>
          <p className="text-lead text-graphite mt-3">
            The page you were after doesn’t exist, or a shared verdict was removed.
          </p>
          <Link
            href="/"
            className="rounded-input bg-ink mt-6 inline-flex min-h-12 items-center px-6 font-medium text-white"
          >
            Go to Worth
          </Link>
        </div>
      </main>
    </div>
  )
}
