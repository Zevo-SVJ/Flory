import type { Metadata } from 'next'
import Link from 'next/link'
import { getProfile, getPreferences } from '@/lib/db/queries'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export const metadata: Metadata = { title: 'Settings', robots: { index: false } }

export default async function SettingsPage() {
  const [profile, preferences] = await Promise.all([getProfile(), getPreferences()])

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-title text-ink font-serif font-medium">Settings</h1>

      <Card className="flex flex-col gap-4 p-5">
        <h2 className="text-muted text-[0.6875rem] font-medium tracking-[0.14em] uppercase">
          Account
        </h2>
        <Row label="Email" value={profile?.email ?? '—'} />
        {profile?.full_name && <Row label="Name" value={profile.full_name} />}
        <p className="text-muted text-[0.8125rem] leading-relaxed">
          To change your email or password, sign out and use{' '}
          <Link href="/forgot-password" className="hover:text-ink underline underline-offset-4">
            reset password
          </Link>
          . Full account management is coming with billing.
        </p>
      </Card>

      <Card className="flex flex-col gap-4 p-5">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-muted text-[0.6875rem] font-medium tracking-[0.14em] uppercase">
            Preferences
          </h2>
          <Link
            href="/onboarding?next=%2Fsettings"
            className="text-muted hover:text-ink text-[0.875rem] underline underline-offset-4"
          >
            Update
          </Link>
        </div>
        <Row
          label="Usually buys"
          value={
            preferences?.spend_categories.length
              ? preferences.spend_categories.join(', ')
              : 'Not set'
          }
        />
        <Row
          label="Cares most about"
          value={
            preferences?.buying_priorities.length
              ? preferences.buying_priorities.join(', ')
              : 'Not set'
          }
        />
        <Row label="Currency" value={preferences?.currency ?? 'EUR'} />
      </Card>

      <Card className="flex flex-col gap-3 p-5">
        <h2 className="text-muted text-[0.6875rem] font-medium tracking-[0.14em] uppercase">
          Session
        </h2>
        <form action="/auth/signout" method="post">
          <Button type="submit" variant="secondary" className="w-full sm:w-auto">
            Sign out
          </Button>
        </form>
      </Card>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-rule flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-t pt-3 first-of-type:border-0 first-of-type:pt-0">
      <span className="text-muted text-[0.875rem]">{label}</span>
      <span className="text-ink text-[0.9375rem]">{value}</span>
    </div>
  )
}
