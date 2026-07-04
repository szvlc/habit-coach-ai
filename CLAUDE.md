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

## 10xDevs AI Toolkit — Moduł 3, Lekcja 3

Lekcja 3 dotyczy **haków** — przekształcania bram jakości z Lekcji 1 i testów z Lekcji 2 w automatyczne, deterministyczne sprawdzenia, które uruchamiają się podczas pracy agenta. Hak działa poza modelem, więc przetrwa kompresję kontekstu, zmiany instrukcji i „zapominanie” przez model. Konkretna korzyść z haków agentowych: sprawdzenie `PostToolUse` może przekazać swój wynik z powrotem do kontekstu agenta, dzięki czemu agent sam naprawia trywialne błędy (formatowanie, brakujący import, zły typ) w następnej iteracji, zamiast abyś Ty odkrywał je minuty później.

```
context/foundation/test-plan.md  (§4 Bramy jakości: jakie sprawdzenie, kiedy wymagane)
        │
        ▼  (przypisz każdą bramę do najtańszej warstwy, która nadal daje sygnał)
   na edycję (haki agenta)  →  pre-commit (haki git)  →  pre-push  →  CI
        │ lint, format, testy zakresowe          │ staged       │ cięższe    │ integracja
        ▼
   kod wyjścia + stdout  →  additionalContext  →  agent reaguje w następnej turze
```

### Router zadań — Która warstwa dla tego sprawdzenia

| Chcesz | Zrób to |
| --- | --- |
| Reaguj natychmiast, gdy agent edytuje plik | Hak na edycję (`PostToolUse` matcher `Write\|Edit` w Claude Code). Odpowiedni do szybkich sprawdzeń: lint/format i testy zakresowe na plikach z obszarów ryzyka. Jest to **jedyna** warstwa, która może przekazać informację zwrotną agentowi w trakcie sesji. |
| Uruchom tylko testy, które zależą od edytowanego pliku | Przeanalizuj ścieżkę z stdin haka (`jq -r .tool_input.file_path`) i uruchom tryb testów powiązanych Twojego runnera (`vitest related "$FILE" --run`, `jest --findRelatedTests $FILE`). Zabezpiecz to, czy plik jest obszarem ryzyka w `test-plan.md`; nie uruchamiaj testów przy każdej edycji pomocnika lub konfiguracji. |
| Wykryj zmiany, które ominęły agenta (ręczne edycje, commit kolegi z zespołu) | Hak git pre-commit (Lefthook lub Husky+lint-staged) na plikach staged: lint + typecheck i testy na staged plikach ryzyka. |
| Uruchom cięższe sprawdzenia, zanim kod opuści maszynę | Pre-push: pełne sprawdzenie typów lub szerszy zestaw testów. Wszystko, co jest zbyt wolne dla edycji, przenosi się tutaj. |
| Zdecyduj, gdzie należy dana brama | Zapytaj: czy jest wystarczająco szybka (kilka sekund) dla edycji, czy powinna poczekać na commit/push/CI? Wolne sprawdzenia blokują pętlę agenta przy każdej edycji — przenieś je o warstwę wyżej. |
| Użyj tego samego haka w różnych narzędziach | Wzór trigger → matcher → handler → signal jest taki sam w Cursor, Codex, Windsurf i Copilot; zmienia się tylko plik konfiguracyjny i nazwy zdarzeń. Zobacz tabelę narzędzi poniżej. |

### Cykl życia haka — uniwersalny wzorzec

Haki każdego narzędzia składają się z czterech kroków:

1. **Trigger** — zdarzenie w narzędziu (np. agent właśnie zapisał plik: `PostToolUse`).
2. **Matcher** — filtr decydujący, czy ten hak ma się uruchomić (nazwa narzędzia, np. `Write`/`Edit`, typ pliku lub wzorzec nazwy).
3. **Handler** — akcja, która się uruchamia, zazwyczaj polecenie shella.
4. **Signal** — wynik wraca do narzędzia. Kod wyjścia mówi o sukcesie/porażce; stdout może przepłynąć do kontekstu agenta jako informacja zwrotna.

### Kody wyjścia i pętla sprzężenia zwrotnego

- **0** — sukces; hak przeszedł, kontynuuj.
- **2** — błąd blokujący; agent widzi informację zwrotną i powinien zareagować.
- **cokolwiek innego** — błąd nieblokujący; logowany, ale nie przerywa pracy.

W przypadku błędu blokującego, stdout przepływa do kontekstu agenta (w Claude Code przez `additionalContext`, z limitem 10 000 znaków; inne narzędzia mają podobne mechanizmy z własnymi limitami). Dlatego agent może sam się korygować: widzi konkretną wiadomość — brakujący typ, niezaimportowany moduł, źle sformatowana linia — a nie tylko „coś się nie udało”.

Granica: agent niezawodnie naprawia **trywialne** poprawki samodzielnie. Gdy test zawiedzie z powodu błędnej logiki biznesowej, hak to ujawnia, ale agent może nie zdiagnozować prawdziwej przyczyny — mówi „coś jest nie tak” i próbuje trywialnej poprawki. Jeśli to nie rozwiąże problemu w jednej lub dwóch próbach, sygnał wraca do Ciebie, a problem może zasługiwać na własny change-id z pełnym przepływem pracy `/10x-new → /10x-research → /10x-plan → /10x-implement`.

### Trzy warstwy lokalne (plus CI)

| Warstwa | Wykrywa | Czas |
| --- | --- | --- |
| Na edycję (haki agenta) | Formatowanie, proste błędy typów, nieudane testy jednostkowe na plikach ryzyka. Jedyna warstwa, która dostarcza agentowi informacji zwrotnej w trakcie pracy. | ms–s |
| Pre-commit (haki git) | Co umknęło na edycję: ręczne edycje, pliki zmienione poza hakiem, sprawdzenia zbyt wolne dla edycji. Działa na plikach staged. | s |
| Pre-push | Cięższe sprawdzenia przed wypchnięciem do zdalnego repozytorium (pełne sprawdzenie typów, szerszy zestaw testów). | s–min |
| CI | Problemy integracyjne, zależności między modułami, sprawdzenia wymagające infrastruktury niedostępnej lokalnie. | min |

Warstwy lokalne **nie** zastępują CI — CI pozostaje kluczową weryfikacją dla współdzielonego stanu repozytorium i środowisk, których nie kontrolujesz. Ale każda lokalna warstwa, która wykryje błąd, to o jedną rundę CI mniej. Nie potrzebujesz wszystkich warstw od pierwszego dnia: zacznij od jednego haka na edycję (lint) i jednej bramy commitu, dodawaj warstwy, gdy zobaczysz, co umyka. Bramy jakości w `test-plan.md §4` decydują, które sprawdzenia warto zautomatyzować i na której warstwie; plan może zasadnie odroczyć haki na edycję, jeśli stosunek koszt/sygnał nie jest jeszcze odpowiedni.

### Kluczowe zasady

- Utrzymuj szybkie haki na edycję. Jeśli sprawdzenie trwa dłużej niż kilka sekund, przenieś je do commitu, pusha lub CI — wolny hak na edycję blokuje pętlę agenta przy każdej edycji. Lint/format są idealne na edycję; pełne sprawdzenie typów jest często bramą commitu w większych projektach.
- Uruchamiaj testy zakresowe, a nie całą suite, na edycję — tylko testy związane z edytowanym plikiem i tylko wtedy, gdy ten plik jest obszarem ryzyka w `test-plan.md`.
- `related` to podpolecenie, a nie flaga (`vitest related`, a nie `--related`). Użyj `--run`, aby hak zakończył działanie zamiast wchodzić w tryb obserwacji.
- `PostToolUse` uruchamia się raz na użycie narzędzia; trzy edycje w jednej turze uruchamiają go trzy razy niezależnie — nie ma wbudowanej agregacji.
- Narzędzie do haków git (Lefthook vs Husky+lint-staged) to szczegół implementacji; zasada jest taka sama — uruchamiaj sprawdzenia na plikach staged przed commitem. Jeśli Husky już działa, nie migruj.
- **Wstrzykiwanie kontekstu nie jest uniwersalne.** Claude Code, Cursor, Codex i Copilot (w VS Code) mogą przekazać wynik haka agentowi; Windsurf nie może — może blokować (exit 2), ale nie może powiedzieć agentowi, co poszło nie tak.

### Ten sam wzorzec w każdym narzędziu

| Narzędzie | Zdarzenia | Handlery | Wstrzykiwanie kontekstu | Konfiguracja |
| --- | --- | --- | --- | --- |
| Claude Code | ~30 | command, http, mcp_tool, prompt, agent | tak | `.claude/settings.json` |
| Cursor | ~18 | command, prompt | tak | `.cursor/hooks.json` |
| Codex | 10 | command | tak | `.codex/hooks.json` |
| Windsurf | 12 | command | **nie** | `.windsurf/hooks.json` |
| Copilot | ~13 | command, http, prompt | tak (VS Code) | `.github/hooks/*.json` |

### Granice lekcji

- Ta lekcja konfiguruje tylko haki i lokalne warstwy jakości. Zakres obejmuje JSON haka, `lefthook.yml` oraz warstwy na edycję/commit/push.
- Nie pisz testów E2E, nie konfiguruj Playwright/MCP ani nie uruchamiaj scenariuszy przeglądarki. To jest Lekcja 4.
- Nie uruchamiaj przepływu pracy debugowania od błędu do poprawki do testu regresji. To jest Lekcja 5.
- Nie zmieniaj strategii ryzyka ani definicji bram jakości. To jest Lekcja 1 (`/10x-test-plan`); odczytaj bieżący stan za pomocą `/10x-test-plan --status`.
- Nie pisz kodu testów jednostkowych/integracyjnych od zera tutaj. To jest Lekcja 2 — haki tylko *uruchamiają* testy, które te lekcje wyprodukowały.
- Nie twórz potoków CI/CD. To jest Moduł 1 Lekcja 5 / Moduł 2 Lekcja 5; haki to warstwy lokalne przed CI.

### Ścieżki używane w tej lekcji

- `.claude/settings.json` — konfiguracja haka (`~/.claude/settings.json` globalny, `.claude/settings.json` projekt, `.claude/settings.local.json` lokalne nadpisania). Inne narzędzia używają własnego pliku konfiguracyjnego (patrz tabela).
- `lefthook.yml` — konfiguracja haka git pre-commit (lint + typecheck + testy na `{staged_files}`).
- `context/foundation/test-plan.md` — §4 bramy jakości decydują, które sprawdzenia zautomatyzować i na której warstwie; obszary ryzyka decydują, które edycje wymagają testów zakresowych.

<!-- END @przeprogramowani/10x-cli -->
