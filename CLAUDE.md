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

## 10xDevs AI Toolkit - Moduł 2, Lekcja 4

Przygotuj się na trudniejszy strumień implementacji z **łańcuchem planowania opartym na badaniach**:

```
badania wewnętrzne (/10x-research) + badania zewnętrzne (exa.ai, Context7) -> /10x-plan -> /10x-implement -> sukces
```

Lekcja koncentruje się na rozróżnianiu badań wewnętrznych od zewnętrznych oraz wykorzystywaniu dowodów do wspierania decyzji planistycznych.

### Router zadań - Od czego zacząć

| Umiejętność | Kiedy jej używać |
| --- | --- |
| **Badania wewnętrzne (fokus lekcji)** | |
| `/10x-research <change-id>` | Potrzebujesz dowodów z istniejącej bazy kodu — wzorców, konwencji, punktów integracji lub istniejących implementacji. Uruchamia równoległe sub-agenty w repozytorium i zapisuje ustrukturyzowane wyniki do `research.md`. |
| **Badania zewnętrzne (fokus lekcji)** | |
| exa.ai | Potrzebujesz natywnego dla AI wyszukiwania w sieci w celu porównania bibliotek, najlepszych praktyk lub kontekstu ekosystemu, na które baza kodu nie może odpowiedzieć. |
| Context7 (`resolve-library-id` → `get-library-docs`) | Potrzebujesz aktualnej dokumentacji dla konkretnej biblioteki lub frameworka. Najpierw rozwiązuje ID biblioteki, a następnie pobiera odpowiednie strony dokumentacji. |
| **Kadrowanie koła zapasowego** | |
| `/10x-frame <change-id>` | Plan nie zbiega się, plan nie przynosi oczekiwanych rezultatów, lub uporczywe odchylenia ciągle psują implementację. Użyj jako wyjścia awaryjnego dla oddzielnego problemu (zademonstrowane na przykładzie Space Explorers), a nie jako rytuału przed badaniami. |
| **Planowanie i wykonanie** | |
| `/10x-plan <change-id>` / `/10x-implement <change-id> phase <n>` | Użyj tego samego łańcucha planowania i wykonania z Lekcji 2, teraz z dowodami z badań wstępnych zasilającymi plan. |

### Dyscyplina badawcza

- Badania wewnętrzne (`/10x-research`) odpowiadają na pytanie "co już robi nasza baza kodu?" — wzorce, schematy, konwencje, punkty integracji.
- Badania zewnętrzne (exa.ai, Context7) odpowiadają na pytanie "co powinniśmy zrobić?" — możliwości bibliotek, dokumentacja API, najlepsze praktyki ek

<!-- END @przeprogramowani/10x-cli -->
