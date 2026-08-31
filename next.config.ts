import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  experimental: {
    // Server Actions receive user-submitted URLs; keep the payload small.
    serverActions: { bodySizeLimit: '1mb' },
  },
}

export default nextConfig
