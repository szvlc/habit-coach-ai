<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Manage habits (S-02)

- **Plan**: context/changes/manage-habits/plan.md
- **Scope**: Phases 1–4 of 4 (full plan)
- **Date**: 2026-06-13
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

### F1 — habits/apps.py omits default_auto_field from plan contract

- **Severity**: 🔵 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: habits/apps.py:5
- **Detail**: Plan Phase 1 §5 specified `HabitsConfig` with `default_auto_field = 'django.db.models.BigAutoField'`. File omits it (only `name = 'habits'`). Harmless: project-wide `DEFAULT_AUTO_FIELD` supplies BigAutoField, migration used BigAutoField correctly, and this matches `accounts/apps.py` (S-01 also omits it).
- **Fix**: Leave as-is (consistent with S-01), or add the line for literal plan fidelity. No behavior change either way.
- **Decision**: SKIPPED — left as-is, consistent with accounts/apps.py (S-01).

### F2 — Concurrent duplicate-name create can still 500 (TOCTOU)

- **Severity**: 🔵 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: habits/views.py:16-18, habits/forms.py:20-26
- **Detail**: The duplicate-name fix (`clean_name` user-scoped check, excludes self.pk for updates, allows cross-user dups, test-covered) is correct for normal use. But the form check and DB insert aren't in one transaction, so two simultaneous submits of the same name by one user could raise IntegrityError → 500. UniqueConstraint is the integrity backstop (no bad data); only the error surface is ugly. Essentially unreachable for a solo-user MVP.
- **Fix**: Accept as risk for the MVP. If concurrency matters later, wrap `form_valid` in try/except IntegrityError → form error.
- **Decision**: ACCEPTED (risk) — backstopped by DB UniqueConstraint; unreachable at solo-user MVP scale. Revisit if concurrency matters.
