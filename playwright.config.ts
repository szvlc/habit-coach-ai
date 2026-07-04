import { defineConfig, devices } from '@playwright/test';
import { readFileSync } from 'fs';

/**
 * Django's settings.py reads raw os.environ and does NOT auto-load .env, so we
 * parse .env here and hand DJANGO_SECRET_KEY (+ DEBUG) to the auto-started dev
 * server. Keeps `npx playwright test` self-contained: no manual env exports.
 */
function loadEnv(): Record<string, string> {
  const env: Record<string, string> = {};
  try {
    for (const line of readFileSync('.env', 'utf-8').split('\n')) {
      const m = line.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*?)\s*$/);
      if (!m) continue;
      let v = m[2];
      if ((v.startsWith("'") && v.endsWith("'")) || (v.startsWith('"') && v.endsWith('"'))) {
        v = v.slice(1, -1);
      }
      env[m[1]] = v;
    }
  } catch {
    /* .env is git-ignored / absent in CI — rely on the ambient environment */
  }
  return env;
}

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:8000',
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'uv run python manage.py runserver 127.0.0.1:8000',
    url: 'http://127.0.0.1:8000/accounts/login/',
    reuseExistingServer: true,
    timeout: 60_000,
    env: { ...loadEnv(), DEBUG: 'True' },
  },
});
