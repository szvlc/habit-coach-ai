<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: First grounded recommendation (S-04)

- **Plan**: context/changes/first-grounded-recommendation/plan.md
- **Scope**: Phases 1–4 of 4 (full plan)
- **Date**: 2026-06-21
- **Verdict**: APPROVED
- **Findings**: 0 critical · 0 warnings · 2 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | PASS |

## Findings

### F1 — LLM output safety relies on autoescape (mark as invariant)

- **Severity**: 🔵 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: templates/habits/_recommendation.html:17
- **Detail**: Model output renders as `{{ recommendation.text }}` (auto-escaped, whitespace-pre-line) — correct today, no `|safe`/markdown. Highest-risk line: a future switch to markdown-to-HTML would turn untrusted LLM text into stored XSS. Currently SAFE; preventive guard, not a defect.
- **Fix**: Add a one-line comment marking "must stay autoescaped — untrusted LLM output".
- **Decision**: FIXED (Fix now) — added SECURITY comment above the render line in _recommendation.html.

### F2 — Empty-state copy duplicated in two places

- **Severity**: 🔵 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: templates/habits/_recommendation.html:32, habits/views.py:118
- **Detail**: "Dodaj nawyk i zaloguj wykonanie…" appears as both the view guard error string and the template empty-state text. Two sources of the same copy can drift. Low impact.
- **Fix**: Leave as-is (skip), or centralize later if it grows.
- **Decision**: SKIPPED — trivial, acceptable for MVP.
