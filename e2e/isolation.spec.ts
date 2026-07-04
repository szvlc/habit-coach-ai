import { test, expect } from '@playwright/test';

/**
 * R1 — Per-user data isolation (test-plan.md § R1, LOAD-BEARING / krytyczne).
 *
 * Risk: one user's habits/executions leak into another user's view. This is the
 * MVP's load-bearing security invariant. Genuinely E2E — it crosses auth,
 * routing, DB querysets, and the rendered dashboard; only a real two-session
 * browser flow proves it end to end.
 *
 * Modeled on e2e/seed.spec.ts (role locators, wait-for-state, unique Date.now()
 * data, cleanup, risk-tied name). Two independent browser CONTEXTS give two
 * isolated sessions without logging in/out through the UI.
 *
 * The assertion FAILS iff R1 materializes: if user B can see user A's habit,
 * toHaveCount(0) fails.
 */
test("R1: a new user cannot see another user's habits (per-user data isolation)", async ({ browser }) => {
  const stamp = Date.now();
  const password = 'Habit!Seed2026';
  const emailA = `e2e-a+${stamp}@example.com`;
  const emailB = `e2e-b+${stamp}@example.com`;
  const secretHabit = `Sekret uzytkownika A ${stamp}`; // unique → no cross-run collision

  // --- User A: register in its own context and create a private habit ---
  const ctxA = await browser.newContext();
  const pageA = await ctxA.newPage();
  await pageA.goto('/register/');
  await pageA.getByLabel('Email').fill(emailA);
  await pageA.getByLabel('Hasło', { exact: true }).fill(password);
  await pageA.getByLabel('Powtórz hasło').fill(password);
  await pageA.getByRole('button', { name: 'Załóż konto' }).click();
  await expect(pageA.getByRole('heading', { name: /Witaj/ })).toBeVisible();

  await pageA.getByRole('link', { name: 'Dodaj swój pierwszy nawyk' }).click();
  await pageA.getByLabel('Nazwa').fill(secretHabit);
  await pageA.getByRole('button', { name: 'Zapisz' }).click();
  await expect(pageA.getByText(secretHabit)).toBeVisible();

  // --- User B: a separate context (independent session) registers fresh ---
  const ctxB = await browser.newContext();
  const pageB = await ctxB.newPage();
  await pageB.goto('/register/');
  await pageB.getByLabel('Email').fill(emailB);
  await pageB.getByLabel('Hasło', { exact: true }).fill(password);
  await pageB.getByLabel('Powtórz hasło').fill(password);
  await pageB.getByRole('button', { name: 'Załóż konto' }).click();
  await expect(pageB.getByRole('heading', { name: /Witaj/ })).toBeVisible();

  // --- Assert the risk: A's habit must NOT appear anywhere in B's dashboard ---
  await expect(pageB.getByText(secretHabit)).toHaveCount(0);
  // And B genuinely sees its own (empty) state, proving the page rendered.
  await expect(pageB.getByText('Nie masz jeszcze żadnych nawyków')).toBeVisible();

  // --- Cleanup: A archives its habit (still logged in in ctxA) ---
  await pageA.getByRole('link', { name: `Archiwizuj nawyk ${secretHabit}` }).click();
  await pageA.getByRole('button', { name: 'Archiwizuj' }).click();
  await expect(pageA.getByText(secretHabit)).toBeHidden();

  await ctxA.close();
  await ctxB.close();
});
