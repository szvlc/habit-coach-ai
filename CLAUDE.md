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

## 10xDevs AI Toolkit — Moduł 3, Lekcja 2

Lekcja 2 dotyczy **pisania testów, które faktycznie chronią kod** — a nie tylko maksymalizują pokrycie. Problem wyroczni i antywzorce testowania na wyczucie wyjaśniają, dlaczego testy generowane przez LLM zawodzą na prawdziwym kodzie; kontrakt jakości oparty na ryzyku z Lekcji 1 jest rozwiązaniem.

```
context/foundation/test-plan.md (§3 Wdrażanie etapowe)
        │
        ▼  (jedna faza wdrażania na raz)
   /10x-research  ──►  research.md  (źródło wyroczni: co kod powinien robić, a nie co robi)
        │
        ▼
   /10x-plan  ──►  plan.md  (koszt × sygnał, dwuwarstwowa strategia, uporządkowane fazy)
        │
        ▼
   /10x-implement  or  /10x-tdd   ──►  działające testy + aktualizacja podręcznika §6
```

`/10x-tdd` to **opcjonalny tryb test-first**, a nie zamiennik dla łańcucha. Odczytuje ten sam `plan.md`, zapisuje do tej samej sekcji `## Progress` i obejmuje te same fazy co `/10x-implement`. Używaj go tylko wtedy, gdy potrafisz nazwać pierwsze nieudane twierdzenie przed napisaniem jakiegokolwiek kodu.

### Router zadań — Od czego zacząć

| Umiejętność / Prompt | Kiedy używać |
| --- | --- |
| `/10x-research` | Przed napisaniem jakiegokolwiek testu dla ryzyka. Badanie tworzy wyrocznię — jakie zachowanie musi udowodnić test — ze źródeł (PRD, tech-stack, dokumentacja), a nie z kształtu implementacji. Ujawnia również, czy ryzyko jest już pokryte, czy ma dwie oddzielne strony (jedną bezpieczną, jedną rzeczywistą). |
| `/10x-plan` | Badanie zakończone. Plan rozkłada ryzyko na uporządkowane fazy: najpierw konfiguracja środowiska, następnie reguły, które od niej zależą, następnie hermetyczne zaślepki dla błędów, których prawdziwa infrastruktura nie może wywołać, a następnie aktualizacja podręcznika. Każda faza nazywa zachowanie, które potwierdza, i regresję, którą wyłapuje. |
| `/10x-implement` | Domyślny wykonawca faz planu. Używaj do konfiguracji środowiska, istniejącego kodu, szkieletowania i każdej fazy, w której nie możesz zdefiniować czerwonego testu przed napisaniem kodu. |
| `/10x-tdd` | Opcjonalne. Używaj zamiast `/10x-implement` dla fazy, w której możesz nazwać pierwszy czerwony test w jednym zdaniu. Agent najpierw pisze nieudany test, następnie minimalny kod, aby go zazielenić, a następnie refaktoryzuje. Zatrzymuje się na twierdzeniu przed dotknięciem implementacji — ta pauza jest kluczowa. |
| prompt `m3l2-ad-hoc-testing` | Masz jeden plik i chcesz testów teraz, bez pełnego cyklu research→plan→implement. Prompt wymusza wyrocznię ze źródeł (czyta PRD + TECH_STACK przed twierdzeniem), twierdzenia behawioralne, przypadki brzegowe z ryzyka i tabelę regresji. Używaj go, wiedząc, że wymieniasz głębię na szybkość. |

### Kiedy używać `/10x-tdd` vs `/10x-implement`

Decydujące pytanie: *Czy potrafisz nazwać pierwszy czerwony test w jednym zdaniu?*

Dobre warunki dla `/10x-tdd`:
- "promuje wyłącznie drafty w stanie `accepted`, a `pending`/`rejected` nigdy nie trafiają do talii"
- "zwraca `ok: true` i loguje `orphan_review_state`, gdy upsert stanu powtórek padnie w trakcie zapisu"
- "zwraca 401, gdy użytkownik nie ma dostępu do kursu"
- "resetuje interwał powtórki do jednego dnia, gdy ocena wynosi 0"

Każde z nich nazywa obserwowalny wynik, a nie wewnętrzny szczegół. Jeśli nie potrafisz stworzyć takiego zdania, pozostań przy `/10x-implement` lub wróć do `/10x-research`.

`/10x-tdd` **nie nadaje się** do: konfiguracji środowiska, konfiguracji CI/CD, dokumentacji, cienkiego okablowania, gdzie test po prostu przepisałby implementację, lub do eksploracji, gdzie nadal odkrywasz kontrakt.

Możesz mieszać oba tryby w jednym planie:

```
/10x-implement <change-id> phase 1   # environment
/10x-tdd       <change-id> phase 2   # contract (new code)
/10x-tdd       <change-id> phase 3   # contract (API endpoint)
/10x-implement <change-id> phase 4   # cookbook + plan sync
```

Oba zapisują postęp do tej samej sekcji `## Progress` w `plan.md`.

### Dwuwarstwowa strategia testowania (koszt × sygnał)

Dla każdego ryzyka wybierz **najtańszy test, który daje prawdziwy sygnał**. Nie domyślnie do e2e "ponieważ jest najbezpieczniejszy" i nie gonić za procentem pokrycia.

| Warstwa | Kiedy używać | Kiedy NIE używać |
| --- | --- | --- |
| Integracja (prawdziwa baza danych / prawdziwa infrastruktura) | Reguła obejmuje ograniczenia bazy danych, kaskady, prawdziwy SQL lub unikalne ograniczenia, o których mock by skłamał. | Przepływy uwierzytelniania zabezpieczone przez RLS, które należą do oddzielnej fazy; wszystko, gdzie koszt konfiguracji przekracza wartość sygnału. |
| Hermetyczne (klient zaślepki) | Częściowe awarie, których prawdziwa infrastruktura nie może łatwo wywołać (np. druga operacja w sekwencji zawodzi). | Reguły, które zależą od rzeczywistego stanu bazy danych — zaślepka skłamie na temat naruszeń ograniczeń i kaskad. |

Niemożliwa do atomowego zapisu sekwencja (wiele niezależnych operacji bez transakcji) oznacza: pisz testy hermetyczne dla gałęzi częściowych awarii, a nie testy integracyjne, które wymuszają błąd w środku sekwencji.

### Reguły wyroczni

- Wyrocznia — co kod *powinien* robić — musi pochodzić ze źródeł: PRD, dokumentacji, ograniczeń stosu technologicznego, wiedzy dziedzinowej. Nie może pochodzić z czytania implementacji.
- Jeśli implementacja ma błąd, skopiowanie jej wyniku jako oczekiwanej wartości tworzy test lustrzany, który przechodzi z błędem.
- Gdy źródła nie rozwiązują jednoznacznie oczekiwanego zachowania, **zatrzymaj się i zapytaj**, zamiast zgadywać.
- Zadaniem badań jest ujawnienie wyroczni przed napisaniem jakiegokolwiek testu.

### Antywzorce testowania na wyczucie, których należy unikać

| Antywzorzec | Jak wygląda | Co robić zamiast |
| --- | --- | --- |
| Implementacja lustrzana | Twierdzenie oblicza oczekiwaną wartość za pomocą tej samej logiki co testowany kod. | Twierdź przeciwko wartości pochodzącej z wyroczni (PRD / reguła dziedzinowa), a nie z implementacji. |
| Tylko szczęśliwe ścieżki | Testy tylko przechodzą prawidłowe dane wejściowe; brak przypadków brzegowych. | Dodaj co najmniej jeden przypadek brzegowy na ryzyko: `null`, pusty, błąd zależności, nieprawidłowe dane wejściowe. |
| Redundantne kopie | Sześć prawie identycznych testów sprawdzających tę samą nieobecność strażnika. | Jeden sparametryzowany test (`it.each`) na właściwość; każdy test wyłapuje inną regresję. |

### Testowanie mutacyjne (Stryker) — selektywna brama jakości

Pokrycie mówi "ta linia została wykonana". Wynik mutacji mówi "czy test by zawiódł, gdybym zepsuł tę linię?". Używaj Strykera jako **selektywnej bramy** po fazie ryzyka, a nie jako bramy CI przy każdym commicie.

Przebieg pracy:
1. Testy przechodzą dla fazy ryzyka.
2. Uruchom `npx stryker run --mutate "path/to/file.ts"` (zawęź zakres do zmienionego modułu).
3. Otwórz raport HTML; znajdź ocalałe mutanty.
4. Dla każdego ocalałego mutanta zadaj pytanie: "Czy ta zmiana zaszkodziłaby użytkownikowi lub firmie?"
   - Tak → dodaj twierdzenie, które zabije mutanta.
   - Nie (równoważny mutant lub zmiana kosmetyczna) → świadomie zignoruj.
5. Nie dąż do 100% wyniku mutacji. Test, który przypina szczegóły implementacji, aby zabić kosmetycznego mutanta, sam w sobie jest testem na wyczucie.

Brama integracyjna może pozostać **ad hoc** (nie przy każdym commicie), gdy uruchamianie lokalnej infrastruktury jest kosztowne. Zaznacz to odpowiednio w `test-plan.md §4`.

### Granice lekcji

- Nie konfiguruj haków, cyklu życia haków ani haków debugowania. To jest Lekcja 3.
- Nie konfiguruj serwerów MCP, API Playwright, kodu e2e ani kodu scenariuszy multimodalnych. To jest Lekcja 4.
- Nie uruchamiaj przepływu pracy od błędu do poprawki do testu regresji. To jest Lekcja 5.
- Nie twórz potoków CI/CD od podstaw. To jest Moduł 1 Lekcja 5 / Moduł 2 Lekcja 5.
- Nie uruchamiaj `/10x-test-plan`, aby zmienić strategię ryzyka. To jest Lekcja 1. Użyj `/10x-test-plan --status`, aby odczytać bieżący stan.
- Nie pisz testów bez kroku badawczego, chyba że używasz promptu ad-hoc z pełną świadomością jego kompromisów.

### Ścieżki używane w tej lekcji

- `context/foundation/test-plan.md` — stan wdrożenia §3; podręcznik §6 (uzupełniany w miarę realizacji faz)
- `context/changes/<change-id>/research.md` — źródło wyroczni dla każdej fazy wdrożenia
- `context/changes/<change-id>/plan.md` — uporządkowane fazy ze stanem wykonania `## Progress`
- `.claude/prompts/m3l2-ad-hoc-testing.md` — prompt do testowania ad-hoc na poziomie pliku

<!-- END @przeprogramowani/10x-cli -->
