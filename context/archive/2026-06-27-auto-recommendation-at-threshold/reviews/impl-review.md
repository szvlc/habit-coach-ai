<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Auto recommendation at threshold (S-06)

- **Plan**: context/changes/auto-recommendation-at-threshold/plan.md
- **Scope**: Phases 1–2 of 2 (full plan)
- **Date**: 2026-06-27
- **Verdict**: APPROVED
- **Findings**: 0 critical · 1 warning · 2 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | PASS |

## Findings

### F1 — Concurrent auto-trigger can double-fire (TOCTOU)

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: habits/views.py:163
- **Detail**: auto_recommendation_due re-check in post() is a TOCTOU guard, not a lock. Two concurrent load-fired POSTs could both pass before either inserts → two proactive rows + two paid LLM calls. No DB uniqueness backstop. Practically unreachable with one synchronous load-trigger per render at MVP scale.
- **Fix A ⭐ Recommended**: Accept as risk (MVP).
  - Strength: Single load-trigger per render makes race practically unreachable; zero complexity.
  - Tradeoff: Rare double-render → duplicate rec + one extra OpenRouter call.
  - Confidence: HIGH — window tiny, cost bounded by max_tokens.
  - Blind spot: None significant at MVP scale.
- **Fix B**: Partial unique constraint on (user) where proactive=True.
  - Strength: DB-level one-proactive-per-user guarantee.
  - Tradeoff: Migration + IntegrityError handling; Postgres partial-index vs SQLite dev.
  - Confidence: MED.
- **Decision**: ACCEPTED (risk) — Fix A. Single synchronous load-trigger per render makes the race practically unreachable at solo-MVP scale; cost bounded by max_tokens. Revisit (Fix B partial unique) if dupes/cost ever appear.

### F2 — Threshold counts archived habits' logs

- **Severity**: 🔵 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: habits/recommendations.py:152-154
- **Detail**: logged_day_count filters habit__user but not habit__archived=False, while history_for (prompt source) excludes archived. A user could cross the threshold on archived-habit logs and get a rec built only from active-habit data. User-scoped (no isolation issue); affects threshold timing only.
- **Fix**: Add `habit__archived=False` to logged_day_count for parity with history_for — or accept (logged history is logged history).
- **Decision**: FIXED (Fix now) — added `habit__archived=False` to logged_day_count; threshold now counts the same active-habit data the prompt uses. 68 tests still green.

### F3 — AND-order: count runs before exists for already-served users

- **Severity**: 🔵 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality (perf)
- **Location**: habits/recommendations.py:161-164
- **Detail**: auto_recommendation_due evaluates the distinct-date count before the proactive-exists check; for users long past threshold the count runs every dashboard load before exists fails it. Cheap (indexed) but reorderable.
- **Fix**: Check `not exists(proactive)` first, then the count.
- **Decision**: FIXED (Fix now) — reordered auto_recommendation_due so the proactive-exists check short-circuits before the distinct-date count for already-served users. Same boolean result; 11 tests green.
