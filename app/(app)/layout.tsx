import Link from 'next/link'
import { redirect } from 'next/navigation'
import { getCurrentUser } from '@/lib/supabase/server'
import { isSupabaseConfigured } from '@/lib/supabase/env'
import { Wordmark } from '@/components/marketing/wordmark'
import { MobileTabBar, DesktopSidebar } from '@/components/app/app-nav'
import { SetupNotice } from '@/components/app/setup-notice'

/**
 * The authenticated shell.
 *
 * This layout re-checks the session independently of proxy.ts. Middleware is a
 * convenience for redirecting early, not an authorisation boundary — and Row
 * Level Security is what actually protects the data underneath.
 */
export default async function AppLayout({ children }: { children: React.ReactNode }) {
  if (!isSupabaseConfigured()) return <SetupNotice />

  const user = await getCurrentUser()
  if (!user) redirect('/login')

  return (
    <div className="flex min-h-dvh flex-col lg:flex-row">
      {/* Mobile top bar */}
      <header className="pt-safe border-rule bg-paper/90 sticky top-0 z-30 border-b backdrop-blur-md lg:hidden">
        <div className="flex h-14 items-center justify-between px-4">
          <Link href="/dashboard" className="rounded-chip" aria-label="Worth">
            <Wordmark />
          </Link>
          <form action="/auth/signout" method="post">
            <button
              type="submit"
              className="rounded-chip text-muted inline-flex min-h-11 items-center px-2 text-[0.875rem]"
            >
              Sign out
            </button>
          </form>
        </div>
      </header>

      {/* Desktop sidebar */}
      <aside className="border-rule hidden w-60 shrink-0 border-r px-4 py-6 lg:flex lg:flex-col lg:gap-8">
        <Link href="/dashboard" className="rounded-chip px-3" aria-label="Worth">
          <Wordmark />
        </Link>
        <DesktopSidebar />
        <form action="/auth/signout" method="post" className="mt-auto">
          <button
            type="submit"
            className="rounded-input text-muted hover:bg-paper-sunk hover:text-ink flex min-h-11 w-full items-center px-3 text-[0.9375rem] transition motion-reduce:transition-none"
          >
            Sign out
          </button>
        </form>
      </aside>

      {/* pb-24 clears the mobile tab bar. */}
      <main className="min-w-0 flex-1 px-4 pt-6 pb-24 sm:px-6 lg:px-10 lg:pt-10 lg:pb-12">
        <div className="mx-auto max-w-3xl">{children}</div>
      </main>

      <MobileTabBar />
    </div>
  )
}
