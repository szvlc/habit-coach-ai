# HabitCoach AI

Aplikacja webowa do śledzenia codziennych nawyków, w której użytkownik dostaje **rekomendacje AI
ugruntowane w jego własnej historii logowania** — a nie generyczne porady. Zamiast „pij więcej wody",
system odwołuje się do konkretów: nazw nawyków, słabych dni tygodnia, streaków i ostatnich przerw.

🔗 **Produkcja:** https://habit-coach-ai.onrender.com

## Funkcje

- **Konta i sesje** — rejestracja, logowanie email + hasło, długa sesja, jawne wylogowanie, reset hasła przez email.
- **Zarządzanie nawykami (CRUD)** — dodawanie, lista, edycja nazwy, archiwizacja (soft-delete zachowujący historię dla AI).
- **Logowanie wykonań** — jednym kliknięciem oznaczasz nawyk jako zrobiony **dziś** (bez logowania wstecz — streaki pozostają uczciwe).
- **Historia 30 dni** — siatka wykonań ostatnich 30 dni.
- **Rekomendacje AI** — generowane na żądanie, cytujące realne dane użytkownika (FR-011).
- **Proaktywna rekomendacja** — automatyczna podpowiedź po przekroczeniu progu zalogowanych danych (FR-013).

## Stos technologiczny

| Warstwa | Technologia |
| --- | --- |
| Backend | Django 6, Python ≥ 3.12 |
| Zarządzanie zależnościami | [uv](https://docs.astral.sh/uv/) (`pyproject.toml` + `uv.lock`) |
| Baza danych | SQLite (dev) · PostgreSQL/Supabase (prod, przez `DATABASE_URL`) |
| Frontend | Szablony Django + Tailwind (CDN) + HTMX |
| AI | OpenRouter (domyślnie `anthropic/claude-haiku-4.5`) |
| Hosting | Render (auto-deploy on push do `main`) |

## Architektura

Standardowy layout Django. Pakiet projektu: `habit_coach_ai/` (ustawienia, URL-e, WSGI/ASGI). Aplikacje:

- **`accounts`** — własny model `User` (email zamiast username, `AUTH_USER_MODEL = 'accounts.User'`), rejestracja, dashboard, logowanie/wylogowanie/reset hasła.
- **`habits`** — modele `Habit`, `HabitExecution`, `Recommendation`; widoki CRUD, toggle wykonania, historia, generowanie rekomendacji AI.

## Wymagania

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

> **Ważne:** projekt jest zarządzany przez `uv` — uruchamiaj polecenia przez `uv run …`, nie wołaj `python`/`pip`/`django-admin` bezpośrednio (rozwiążą się poza `.venv/`).

## Uruchomienie lokalne

```bash
# 1. Zainstaluj zależności (tworzy .venv z uv.lock)
uv sync

# 2. Ustaw zmienne środowiskowe.
#    settings.py czyta surowe os.environ — plik .env NIE jest ładowany automatycznie.
#    Minimalnie wymagane do dev:  DJANGO_SECRET_KEY + DEBUG=True
#
#    Linux/macOS/Git Bash (z pliku .env):
#       set -a; source .env; set +a
#    Windows PowerShell:
#       $env:DJANGO_SECRET_KEY = "<dowolny-długi-losowy-ciąg>"; $env:DEBUG = "True"

# 3. Zastosuj migracje (dev → SQLite db.sqlite3)
uv run python manage.py migrate

# 4. (opcjonalnie) konto superużytkownika do panelu /admin/
uv run python manage.py createsuperuser

# 5. Start serwera dev
uv run python manage.py runserver
```

Aplikacja: http://127.0.0.1:8000/

Przykładowy `.env` do dev:

```dotenv
DJANGO_SECRET_KEY='zmień-na-długi-losowy-ciąg-min-50-znaków'
DEBUG=True
# OPENROUTER_API_KEY=sk-or-...   # opcjonalne; bez niego rekomendacje AI zwrócą błąd
```

## Zmienne środowiskowe

| Zmienna | Wymagana | Domyślnie | Opis |
| --- | --- | --- | --- |
| `DJANGO_SECRET_KEY` | ✅ tak | — | Sekret Django (brak = błąd przy starcie; bez fallbacku). |
| `DEBUG` | nie | `False` | `True` w dev (dodaje localhost do `ALLOWED_HOSTS`, włącza SQLite). |
| `ALLOWED_HOSTS` | prod | `""` | Lista hostów po przecinku (prod: `.onrender.com`). |
| `DATABASE_URL` | prod | — | Jeśli ustawione → PostgreSQL; w przeciwnym razie SQLite. |
| `OPENROUTER_API_KEY` | dla AI | `""` | Klucz OpenRouter; bez niego generowanie rekomendacji zwróci błąd. |
| `OPENROUTER_MODEL` | nie | `anthropic/claude-haiku-4.5` | Model LLM. |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | dla maili | — | Wysyłka maila resetu hasła (w dev bez konfiguracji maile trafiają do konsoli). |

## Testy

72 testy adresujące konkretne ryzyka (izolacja danych per-user, ugruntowanie AI, brak logowania
wstecz, bezpieczeństwo auth/wylogowania, próg proaktywny). Ryzyka i mapowanie na testy:
**[`context/foundation/test-plan.md`](context/foundation/test-plan.md)**.

```bash
uv run python manage.py test            # cały zestaw (72)
uv run python manage.py test accounts   # konta / auth / logout
uv run python manage.py test habits     # nawyki / wykonania / rekomendacje
```

## Bezpieczeństwo (guardrail nadrzędny)

**Izolacja danych per-user.** Nawyki, wykonania i rekomendacje jednego użytkownika nigdy nie są
widoczne dla innego ani dla gościa — każdy widok i queryset filtruje po `request.user`, dostęp do
cudzego zasobu zwraca 404. To load-bearing invariant MVP, pokryty testami z grupy R1 w test-planie.

## Deployment

Render robi **auto-deploy na każdy push do `main`** (konfiguracja w [`render.yaml`](render.yaml)):
`uv sync --frozen` → `collectstatic` → `migrate` (pre-deploy) → `gunicorn`. Sekrety
(`DJANGO_SECRET_KEY`, `DATABASE_URL`, `OPENROUTER_API_KEY`) ustawione w panelu Render.

## Dokumentacja

- [`context/foundation/prd.md`](context/foundation/prd.md) — wymagania produktowe (PRD)
- [`context/foundation/roadmap.md`](context/foundation/roadmap.md) — mapa drogowa MVP
- [`context/foundation/test-plan.md`](context/foundation/test-plan.md) — plan testów (ryzyka → testy)
- [`context/foundation/tech-stack.md`](context/foundation/tech-stack.md) — wybór stosu
- [`CLAUDE.md`](CLAUDE.md) — instrukcje dla agentów AI pracujących w repo
