import { test, expect } from '@playwright/test';

/**
 * SEED E2E TEST — the exemplar every generated E2E test is modeled on.
 * "What you show is what you get." (see .claude/skills/10x-e2e/references/)
 *
 * Conventions demonstrated (mirror these in every generated test):
 *  1. Role-based locators — getByRole / getByLabel / getByText, never CSS/XPath.
 *  2. Test independence — one self-contained cycle: setup → action → assert → cleanup.
 *  3. Wait for STATE, not time — expect(...).toBeVisible() / waitForURL(),
 *     never page.waitForTimeout().
 *  4. Unique test data — Date.now() suffix so parallel runs / re-runs never collide.
 *  5. Risk-tied name — the title binds the test to a risk in
 *     context/foundation/test-plan.md, and the assertion fails iff that risk materializes.
 *
 * Auth note: individual tests should reuse a captured session via storageState
 * (global setup) — never log in through the UI. The seed registers a fresh unique
 * user inline because it deliberately demonstrates the full lifecycle end to end.
 *
 * Assumes playwright.config.ts sets `use.baseURL = 'http://127.0.0.1:8000'`.
 */

// R3 — No backdated logging / execution integrity: an execution marked "done"
// for today must persist (survive a reload). If R3 breaks, the toggled state is
// lost on refresh and this test fails.
test('R3: habit marked done today stays done after reload', async ({ page }) => {
  const stamp = Date.now();
  const email = `e2e+${stamp}@example.com`;
  const password = 'Habit!Seed2026';
  const habitName = `Bieganie ${stamp}`; // unique data → no collision on re-run

  // --- Setup: register a fresh, isolated user (auto-logs in → dashboard) ---
  await page.goto('/register/');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Hasło', { exact: true }).fill(password);
  await page.getByLabel('Powtórz hasło').fill(password);
  await page.getByRole('button', { name: 'Załóż konto' }).click();

  // Wait for STATE (landed on dashboard), not a fixed timeout.
  await expect(page.getByRole('heading', { name: /Witaj/ })).toBeVisible();

  // --- Setup: create a habit with a unique name ---
  await page.getByRole('link', { name: 'Dodaj swój pierwszy nawyk' }).click();
  await page.getByLabel('Nazwa').fill(habitName);
  await page.getByRole('button', { name: 'Zapisz' }).click();
  await expect(page.getByText(habitName)).toBeVisible();

  // --- Action: mark it done today ---
  await page.getByRole('button', { name: 'Oznacz wykonane' }).click();
  // Web-first assertion auto-retries until the HTMX swap lands.
  await expect(page.getByRole('button', { name: /Zrobione dziś/ })).toBeVisible();

  // --- Assert the risk: state survives a full page reload (persisted, not just DOM) ---
  await page.reload();
  await expect(page.getByRole('button', { name: /Zrobione dziś/ })).toBeVisible();

  // --- Cleanup: archive the habit we created (unique email keeps the user harmless) ---
  await page.getByRole('link', { name: `Archiwizuj nawyk ${habitName}` }).click();
  await page.getByRole('button', { name: 'Archiwizuj' }).click();
  await expect(page.getByText(habitName)).toBeHidden();
});
