import { defineConfig, devices } from '@playwright/test'

/**
 * Responsive verification.
 *
 * Runs against a production build. Horizontal overflow and undersized touch
 * targets are failing checks here rather than something discovered on a phone.
 */
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  reporter: [['list']],
  /* Playwright owns the server, so a test run can never hit a stale build. */
  webServer: {
    command: 'npx next start -p 3100',
    url: 'http://localhost:3100',
    reuseExistingServer: false,
    timeout: 60_000,
  },
  use: {
    baseURL: process.env.BASE_URL ?? 'http://localhost:3100',
    ...devices['Desktop Chrome'],
    launchOptions: { executablePath: process.env.CHROMIUM_PATH || undefined },
  },
})
