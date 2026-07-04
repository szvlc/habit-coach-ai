# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

HabitCoach AI — a Django web app where users log daily habits and receive AI-generated recommendations grounded in their own logging history. Greenfield, solo, 3-week MVP target, after-hours. Canonical context lives in `@context/foundation/prd.md` and `@context/foundation/tech-stack.md`; the scaffold audit trail is `@context/changes/bootstrap-verification/verification.md`.

## Hard guardrails (PRD-derived, non-negotiable)

- **Per-user data isolation.** Habits, execution logs, and recommendations of one user MUST NEVER be visible to another user or to a logged-out visitor (PRD § Success Criteria — Guardrails). Every view, queryset, and template path that touches user data must filter by `request.user`. This is the load-bearing security invariant for the MVP — every code review checks it explicitly.
- **AI recommendations cite the user's own data.** Each recommendation must reference concrete elements of that user's logged history (habit names, weak-day patterns, streaks, recent breaks). Generic advice ("drink more water", "sleep 8 hours") violates the Primary success criterion of ≥ 75 % data-specific recommendations (PRD § Success Criteria, FR-011, FR-013).
- **No backdated logging.** Execution toggling is allowed only for the current day; backward edits and undos beyond today are blocked to keep streaks honest for the AI (FR-009). Treat this as a domain rule, not a UI nicety.

## Commands

The project is uv-managed (`pyproject.toml` + `uv.lock`). Route every Python command through `uv` — do NOT call `python`, `pip`, or `django-admin` directly, because they will resolve outside `.venv/`.

- Dev server: `uv run python manage.py runserver`
- Apply migrations: `uv run python manage.py migrate`
- Generate migrations: `uv run python manage.py makemigrations`
- Run tests: `uv run python manage.py test`
- Run a single test: `uv run python manage.py test <app>.tests.<TestClass>.<test_method>` (Django's default test runner; pytest is not configured)
- Create superuser (for the built-in Django admin): `uv run python manage.py createsuperuser`
- Add a runtime dependency: `uv add <pkg>` (never `pip install`)
- Re-run the dependency vulnerability audit: `uv run --with pip-audit pip-audit`

No linter, formatter, or CI is wired yet — these are explicitly scoped for later lessons in the chain. Do not invent commands for tools that are not in `pyproject.toml`.

## Architecture

Standard Django `startproject` layout: `manage.py` at the repo root, the project package at `habit_coach_ai/` (settings, root URLs, ASGI/WSGI). **No Django apps have been created yet** — the first concrete feature task will be `uv run python manage.py startapp <name>` plus wiring the new app into `habit_coach_ai/settings.INSTALLED_APPS` and `habit_coach_ai/urls.py`.

Naming detail to avoid confusion: the on-disk Python package is `habit_coach_ai` (snake_case, required by Django's module-naming rules). The canonical `project_name` in `context/foundation/tech-stack.md` is `habit-coach-ai` (kebab-case). Both are correct in their own context; the rationale is logged in `context/changes/bootstrap-verification/verification.md`.

Database is SQLite in dev (Django defaults in `habit_coach_ai/settings.py`); PostgreSQL is the planned prod target per the tech-stack hand-off. Deployment target is Fly.io with GitHub Actions auto-deploy-on-merge (none wired yet — see `@context/foundation/tech-stack.md` `hints`). The proactive recommendation in FR-013 is modeled as a request-time check, not a background job — Django does not need Celery/RQ for the MVP.

`SECRET_KEY` in `habit_coach_ai/settings.py` and `DEBUG = True` are the auto-generated startproject defaults. Both must move behind environment variables before any deploy work.

## 10xDevs toolkit conventions

This repo is bootstrapped through `@przeprogramowani/10x-cli`. The chain so far: `/10x-init → /10x-shape → /10x-prd → /10x-tech-stack-selector → /10x-bootstrapper`, with `/10x-agents-md`, `/10x-rule-review`, and `/10x-lesson` available for the agent-context phase. Skills live in `.claude/skills/`; durable workflow artifacts live under `context/foundation/` (PRD, shape-notes, tech-stack) and `context/changes/` (per-change folders, including the bootstrap audit log).

**Do not edit the block below between the `BEGIN`/`END @przeprogramowani/10x-cli` markers** — `10x get` regenerates it on every lesson fetch. Add new project-specific guidance ABOVE this paragraph so it survives re-fetches.

<!-- BEGIN @przeprogramowani/10x-cli -->

## 10xDevs AI Toolkit - Moduł 2, Lekcja 5

Skaluj cykl pojedynczych zmian do pracy równoległej za pomocą **worktrees, delegowania ukierunkowanego na cel i orkiestracji wielu sesji**:

```
worktree per change -> /goal or claude -p -> PR -> review -> merge
```

Lekcja koncentruje się na bezpiecznej przepustowości: izolowanych kontekstach, wyborze odpowiedniego trybu wykonania i ograniczeniu równoległości do zdolności przeglądu.

### Router zadań - Od czego zacząć

| Umiejętność | Kiedy jej używać |
| --- | --- |
| **Izolacja kodu** | |
| `git worktree add` | Potrzebujesz oddzielnego katalogu roboczego dla równoległej zmiany. Jedna zmiana na worktree, jeden świeży kontekst agenta na worktree. |
| **Złożone zmiany** | |
| `/10x-implement <change-id> phase <n>` | Zmiana ma wiele faz, wymaga ręcznych bramek lub korzysta z interaktywnego podejmowania decyzji podczas wykonania. |
| **Proste zmiany** | |
| `/goal` | Masz jasne, ograniczone zadanie i chcesz delegowania ukierunkowanego na cel. Agent pracuje autonomicznie w kierunku określonego celu z warunkiem zatrzymania. |
| `claude -p` | Chcesz bezgłowego wykonania dla dobrze zdefiniowanego zadania. Pętla Ralpha Wigguma (uruchom, sprawdź, spróbuj ponownie) to uniwersalny autonomiczny wzorzec. |
| **Orkiestracja wielu sesji** | |
| Superset / Conductor / Antigravity / VS Code Agent View | Uruchamiasz wiele sesji agentów równolegle i potrzebujesz widoczności, koordynacji lub zarządzania sesjami między nimi. |

### Zasady pracy równoległej

- Jedna zmiana na worktree lub izolowany obszar roboczy. Jeden świeży kontekst agenta na zmianę.
- Wybierz interaktywne `/10x-implement` dla złożonych zmian, `/goal` lub `claude -p` dla prostych.
- Równoległość jest ograniczona przez zdolność przeglądu. Więcej agentów bez przeglądu oznacza więcej nieprzejrzanego kodu, a nie wyższą przepustowość.
- Ból jakości wynikający z szybszej wysyłki jest celowy — łączy się z bramkami testowymi Modułu 3.

### Granice lekcji

- Nie ucz ponownie interaktywnego `/10x-implement` ani `/10x-impl-review`; to są Lekcje 2 i 3.
- Nie wprowadzaj tutaj strategii testowania. Ból jakości jest motywacją dla Modułu 3.
- Worktrees to mechanizm izolacji, a nie temat pełnego samouczka git.

### Ścieżki używane w tej lekcji

- `context/changes/<change-id>/` - aktywny folder zmian
- `context/changes/<change-id>/plan.md` - dane wejściowe implementacji dla dowolnego trybu wykonania

Umiejętności nie mogą zapisywać do `context/archive/`. Zarchiwizowane zmiany są niezmienne; jeśli rozwiązana ścieżka docelowa zaczyna się od `context/archive/`, przerwij z komunikatem: "Ta zmiana jest zarchiwizowana. Zamiast tego otwórz nową zmianę za pomocą `/10x-new`."

<!-- END @przeprogramowani/10x-cli -->
