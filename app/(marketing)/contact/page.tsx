import type { Metadata } from 'next'
import { LegalPage } from '../legal-layout'

export const metadata: Metadata = {
  title: 'Contact',
  description: 'How to reach the people building Worth.',
}

export default function ContactPage() {
  return (
    <LegalPage title="Contact">
      <p>
        Worth is being built in the open and hasn’t launched, so this is a small operation rather
        than a support desk.
      </p>
      <p>
        <strong>A contact address hasn’t been set up yet.</strong> Rather than print one that
        bounces, this page will carry it as soon as it exists — along with how to request your data
        or delete your account.
      </p>
      <p>
        If you’re reading this because something on the site is wrong or misleading, that’s
        genuinely worth hearing about.
      </p>
    </LegalPage>
  )
}
