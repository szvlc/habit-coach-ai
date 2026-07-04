import { test, expect } from '@playwright/test';

/**
 * R4 — Auth / safe logout (test-plan.md § R4, krytyczne).
 *
 * Risk: after logging out, the session must be invalidated so protected
 * resources are no longer reachable. If logout leaves the session alive,
 * navigating back to the dashboard "/" would still render it — a critical
 * auth failure. This risk is genuinely E2E: it crosses auth + routing +
 * session (login-required redirect only materializes end-to-end).
 *
 * Modeled on e2e/seed.spec.ts:
 *  1. Role-based locators only (getByRole / getByLabel / getByText).
 *  2. Independent — registers its own fresh, unique user inline.
 *  3. Waits for STATE (toBeVisible / waitForURL), never waitForTimeout.
 *  4. Unique data (Date.now() suffix) so re-runs never collide.
 *  5. Risk-tied name; the assertion FAILS iff R4 materializes.
 *
 * Assumes playwright.config.ts sets use.baseURL = 'http://127.0.0.1:8000'.
 */
test('R4: logging out invalidates the session so the dashboard is unreachable and redirects to login', async ({ page }) => {
  const stamp = Date.now();
  const email = `e2e+${stamp}@example.com`;
  const password = 'Habit!Seed2026';

  // --- Setup: register a fresh, isolated user (auto-logs in → dashboard) ---
  await page.goto('/register/');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Hasło', { exact: true }).fill(password);
  await page.getByLabel('Powtórz hasło').fill(password);
  await page.getByRole('button', { name: 'Załóż konto' }).click();

  // Wait for STATE: we are authenticated and on the dashboard.
  await expect(page.getByRole('heading', { name: /Witaj/ })).toBeVisible();
  // The authenticated header exposes the logout control.
  const logout = page.getByRole('button', { name: 'Wyloguj' });
  await expect(logout).toBeVisible();

  // --- Action: log out via the POST form button in the header ---
  await logout.click();

  // --- Assert the risk: the session is dead. ---
  // 1) Logout redirected us off the authenticated view onto the login page.
  await expect(page.getByRole('heading', { name: 'Zaloguj się' })).toBeVisible();

  // 2) The load-bearing check — try to reach the dashboard again. If the
  //    session survived logout (R4 materializes), "/" would render the
  //    dashboard heading and this test must fail. A dead session forces a
  //    redirect to the login page instead.
  await page.goto('/');
  await page.waitForURL(/\/accounts\/login\//);
  await expect(page).toHaveURL(/\/accounts\/login\//);
  await expect(page.getByRole('heading', { name: 'Zaloguj się' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Zaloguj się' })).toBeVisible();
  // Guard against a false pass: the protected dashboard must NOT be shown.
  await expect(page.getByRole('heading', { name: /Witaj/ })).toBeHidden();

  // --- Cleanup: the session is already invalidated; the unique-email user
  //     holds no habits/executions, so it is inert. No shared state remains. ---
});
