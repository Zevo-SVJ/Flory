import type { Metadata } from 'next'
import { LegalPage } from '../legal-layout'

export const metadata: Metadata = {
  title: 'Terms',
  description: 'The short version, while Worth is pre-launch.',
}

export default function TermsPage() {
  return (
    <LegalPage title="Terms">
      <p>
        <strong>Worth hasn’t launched.</strong> There is nothing to buy, no billing, and no paid
        plan running. Full terms will be published before that changes.
      </p>
      <p>
        <strong>The research engine isn’t connected.</strong> Every score, verdict, price and piece
        of evidence shown on this site or produced by the app today comes from development fixture
        data. It is labelled as such wherever it appears. Do not make a purchase decision from it.
      </p>
      <p>
        <strong>When it is connected,</strong> a Worth verdict will be an opinion assembled from
        public information, not financial advice and not a guarantee about any product, price or
        seller. The evidence sits under every verdict so you can check it and disagree.
      </p>
      <p>
        <strong>Your account.</strong> Don’t use Worth to break the law or to hammer other people’s
        sites through it. We may suspend accounts that do. You can delete yours whenever you like.
      </p>
      <p>
        <a href="/contact">Contact us</a> with anything unclear.
      </p>
    </LegalPage>
  )
}
