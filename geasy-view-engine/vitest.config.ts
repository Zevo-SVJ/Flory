import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  test: {
    include: ["tests/**/*.test.ts"],
    testTimeout: 30_000,
    hookTimeout: 30_000,
    fileParallelism: false,
    env: {
      DATABASE_URL: "postgres://geasy:geasy@127.0.0.1:5432/geasy_test",
      REDIS_URL: "redis://127.0.0.1:6379/9",
      ENCRYPTION_KEY: "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      PUBLIC_BASE_URL: "https://geasy.test",
      TELEGRAM_API_BASE: "http://127.0.0.1:18999",
      WORKER_PORT: "14000",
      LOG_LEVEL: "error",
    },
    globalSetup: ["tests/global-setup.ts"],
  },
});
