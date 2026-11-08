import path from "node:path";
import type { NextConfig } from "next";

const config: NextConfig = {
  // Docker uses the standalone server; Vercel builds its own output.
  output: process.env.VERCEL ? undefined : "standalone",
  turbopack: { root: path.resolve(__dirname) },
  outputFileTracingRoot: path.resolve(__dirname),
  poweredByHeader: false,
  serverExternalPackages: ["pg", "bullmq", "ioredis", "telegram"],
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "same-origin" },
          { key: "X-Robots-Tag", value: "noindex, nofollow" },
        ],
      },
    ];
  },
};

export default config;
