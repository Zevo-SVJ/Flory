import type { Metadata } from 'next'
import { LegalPage } from '../legal-layout'

export const metadata: Metadata = {
  title: 'Privacy',
  description: 'What Worth stores, and what it doesn’t.',
}

export default function PrivacyPage() {
  return (
    <LegalPage title="Privacy">
      <p>
        <strong>Worth hasn’t launched.</strong> This is a plain description of what the product
        stores today, not a finished legal policy. A full one will be published before Worth takes
        any money.
      </p>
      <p>
        <strong>What’s stored.</strong> Your email address and, if you sign in with Google, the name
        and avatar Google returns. The categories and priorities you pick during onboarding, which
        are optional and skippable. Every link you submit for analysis, its result, and any
        screenshot you upload.
      </p>
      <p>
        <strong>Who can see it.</strong> Only you. Access is enforced at the database with row level
        security rather than in application code, and uploaded screenshots live in a private bucket
        scoped to your account.
      </p>
      <p>
        <strong>Shared results.</strong> If you create a share link, the public page shows the
        score, the verdict, the money and the signals. It never exposes the link you analysed, the
        screenshot you uploaded, or who you are.
      </p>
      <p>
        <strong>What isn’t collected.</strong> There is no analytics or advertising tracking on this
        site, and Worth takes no affiliate commission — nothing about how it is paid depends on you
        buying anything.
      </p>
      <p>
        Questions, or want your account deleted? <a href="/contact">Get in touch</a>.
      </p>
    </LegalPage>
  )
}
