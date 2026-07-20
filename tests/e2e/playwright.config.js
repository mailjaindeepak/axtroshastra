// Playwright config for Axtroshastra UI/E2E tests.
// Runs every spec against BOTH a mobile and a desktop viewport, so layout
// regressions (like a squeezed dropdown) fail the build.
//
// The app under test is expected at E2E_BASE_URL (default http://localhost:8000).
// Start it first with SQLite + demo mode, e.g.:
//   DEMO_MODE=1 DB_PATH=/tmp/qa.db uvicorn api:app --port 8000
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: '.',
  timeout: 30_000,
  expect: { timeout: 8_000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:8000',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'mobile',  use: { ...devices['Pixel 5'] } },
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
  ],
});
