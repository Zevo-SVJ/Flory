import type { MetadataRoute } from 'next'
import { siteUrl } from '@/lib/supabase/env'

export default function sitemap(): MetadataRoute.Sitemap {
  const base = siteUrl()
  return [
    { url: base, changeFrequency: 'weekly', priority: 1 },
    { url: `${base}/pricing`, changeFrequency: 'monthly', priority: 0.6 },
  ]
}
