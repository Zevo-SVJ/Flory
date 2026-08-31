import type { Metadata, Viewport } from 'next'
import { Inter, Newsreader } from 'next/font/google'
import { siteUrl } from '@/lib/supabase/env'
import './globals.css'

/* Interface and data. Tabular numerals carry the scores and prices. */
const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
})

/* Editorial voice: headlines and the verdict's reason. Used sparingly. */
const newsreader = Newsreader({
  subsets: ['latin'],
  variable: '--font-newsreader',
  display: 'swap',
  weight: ['400', '500'],
})

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl()),
  title: {
    default: 'Worth — Is it actually worth it?',
    template: '%s · Worth',
  },
  description:
    'Paste what you’re thinking about buying. Worth investigates the price, reviews, risks and alternatives, then gives you a clear verdict — buy, think twice or skip.',
  applicationName: 'Worth',
  alternates: { canonical: '/' },
  openGraph: {
    type: 'website',
    siteName: 'Worth',
    title: 'Worth — Is it actually worth it?',
    description:
      'Paste what you’re thinking about buying. Worth investigates the price, reviews, risks and alternatives, then helps you decide.',
    url: '/',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Worth — Is it actually worth it?',
    description: 'A clear verdict on what you’re about to spend money on.',
  },
}

export const viewport: Viewport = {
  themeColor: '#fafaf8',
  width: 'device-width',
  initialScale: 1,
  // Covers the notch; pinch-zoom stays available (never user-scalable: no).
  viewportFit: 'cover',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${newsreader.variable}`}>
      <head>
        {/*
          Marks the document as JavaScript-capable before first paint. Scroll
          reveals only hide content when this class is present, so a visitor
          with JavaScript blocked or broken still sees the whole page.
        */}
        <script
          dangerouslySetInnerHTML={{
            __html: `document.documentElement.classList.add('js')`,
          }}
        />
      </head>
      <body className="min-h-dvh antialiased">{children}</body>
    </html>
  )
}
