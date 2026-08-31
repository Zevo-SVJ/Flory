import type { MetadataRoute } from 'next'
import { siteUrl } from '@/lib/supabase/env'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      // Private surfaces. Shared results at /w/ stay indexable — they are the
      // top of the funnel.
      disallow: ['/dashboard', '/analyze', '/history', '/settings', '/onboarding', '/auth/'],
    },
    sitemap: `${siteUrl()}/sitemap.xml`,
  }
}
