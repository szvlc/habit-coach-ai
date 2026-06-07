---
project: HabitCoach AI
version: 1
status: draft
created: 2026-05-30
updated: 2026-06-07
prd_version: 1
main_goal: market-feedback
top_blocker: decisions
---

# Mapa drogowa: HabitCoach AI

> Wywiedziono z `context/foundation/prd.md` (v1) + automatycznie zbadana baza kodu z 2026-05-30.
> Edytuj na miejscu; archiwizuj po zastąpieniu (zgodnie z konwencją `context/foundation/`).
> Poniższe wycinki są wymienione w kolejności zależności. Tabela „W skrócie" to indeks.

## Podsumowanie wizji

Osoby pracujące umysłowo (25–40 lat) próbują budować nawyki samorozwojowe, ale po 2–3 tygodniach logowania widzą historię w aplikacji i nie wiedzą, co z nią zrobić — dane są obecne, znaczenie nie. HabitCoach AI generuje rekomendacje cytujące rzeczywiste wzorce konkretnego użytkownika (nie generyczne porady), żeby dane zaczęły mówić. To wyróżnik produktu i jedyna hipoteza, którą MVP ma walidować.

Sekwencja jest sortowana pod kątem `market-feedback`: szybkie wystawienie ścieżki, która generuje sygnał, czy ugruntowane rekomendacje AI faktycznie rezonują z prawdziwymi użytkownikami. Wszystko inne (FR poza tą ścieżką walidacyjną) ma znaczenie tylko wtedy, gdy ten moment się zdarza.

## Gwiazda przewodnia

**S-04: Pierwsza ugruntowana rekomendacja AI cytująca rzeczywistą historię użytkownika.** Jednoznaczny kamień milowy walidacji hipotezy z PRD §Vision: użytkownik klika „Wygeneruj rekomendację" i widzi tekst odnoszący się do swoich konkretnych nawyków i ich wzorca wykonań — nie generyczną poradę.

> Termin „gwiazda przewodnia" oznacza tutaj najmniejszy kompleksowy wycinek, którego pomyślne dostarczenie udowadnia podstawową hipotezę produktu — wystawia FR-011/012 z FR-005 + FR-008 w łańcuchu wymagań, a Primary Success Criterion (≥ 75% rekomendacji cytuje konkretne dane) można dopiero wtedy zacząć mierzyć. Umieszczona możliwie wcześnie w sekwencji, na ile pozwalają zależności.

## W skrócie

| ID    | Change ID                              | Wynik (użytkownik może…)                                                   | Wymagania wstępne | Odnośniki PRD                  | Status   |
| ----- | -------------------------------------- | -------------------------------------------------------------------------- | ----------------- | ------------------------------ | -------- |
| F-01  | `render-deploy-operational`            | (fundament) pierwszy Render deploy zielony, Supabase Postgres osiągalny    | —                 | infrastructure.md §Recommendation | done     |
| S-01  | `register-and-login`                   | zarejestrować konto i zalogować się email+hasło z długą sesją              | F-01              | US-01, FR-001, FR-002          | done     |
| S-02  | `manage-habits`                        | dodać, edytować nazwę i zarchiwizować nawyk                                | S-01              | US-01, FR-005, FR-006, FR-007  | proposed |
| S-03  | `log-execution-and-history`            | jednym kliknięciem zalogować wykonanie i zobaczyć 30 dni historii          | S-02              | US-01, FR-008, FR-009, FR-010  | proposed |
| S-04  | `first-grounded-recommendation`        | wygenerować rekomendację AI cytującą jego rzeczywistą historię             | S-03              | US-01, FR-011, FR-012          | proposed |
| S-05  | `password-reset-via-email`             | zresetować zapomniane hasło przez link na email                            | S-01              | FR-003                         | blocked  |
| S-06  | `auto-recommendation-at-threshold`     | zobaczyć proaktywną rekomendację AI po przekroczeniu progu danych          | S-04              | FR-013                         | blocked  |
| S-07  | `logout`                               | wylogować się jawnie (poza wygaśnięciem sesji)                             | S-01              | FR-004                         | proposed |

## Strumienie

Pomoc nawigacyjna — grupuje elementy, które współdzielą łańcuch wymagań. Kanoniczna kolejność nadal jest w grafie zależności poniżej; ta tabela to proponowana kolejność czytania w równoległych ścieżkach.

| Strumień | Temat                | Łańcuch                                              | Uwaga                                                                              |
| -------- | -------------------- | ---------------------------------------------------- | ---------------------------------------------------------------------------------- |
| A        | Ścieżka walidacji    | `F-01` → `S-01` → `S-02` → `S-03` → `S-04` → `S-06` | Główna oś pod `main_goal: market-feedback`; kulminacja w S-04 (gwiazda przewodnia). |
| B        | Cykl życia konta     | `S-05` / `S-07`                                      | Oba rozgałęziają się od `S-01` i są równolegle ze Streamem A; S-05 zablokowany.    |

## Baza

Co już jest na miejscu w bazie kodu na 2026-05-30 (automatycznie zbadane + potwierdzone przez użytkownika). Poniższe wycinki zakładają obecność tych warstw i ich NIE odbudowują.

- **Frontend:** nieobecny — tech-stack.md nie deklaruje SPA frameworka. Django renderuje server-rendered HTML; szablony tworzone w slice'ach, które ich potrzebują.
- **Backend / API:** obecny — Django 6.0 scaffold w `habit_coach_ai/`. INSTALLED_APPS to tylko Django built-ins; project apps tworzone przez `startapp` w slice'ach.
- **Dane:** częściowy — `dj-database-url` + `psycopg[binary]` zainstalowane, `DATABASES` parsowane z `DATABASE_URL` (Supabase Postgres planowane). Brak project models / migracji.
- **Uwierzytelnianie:** szkielet obecny — `django.contrib.auth` zarejestrowany, built-in `User` model + `AUTH_PASSWORD_VALIDATORS`. Brak project views/templates/urls dla FR-001..003.
- **Wdrożenie / infrastruktura:** częściowy — `render.yaml` Blueprint zacommitowany, Render service utworzony przez Blueprint, pierwszy deploy w toku (currently failing na config `DATABASE_URL` — taktyczne, kończone w F-01). GitHub remote prywatny.
- **Obserwowalność:** nieobecny — brak Sentry / strukturyzowanego logowania / metryk. Poza scope MVP.

## Fundamenty

### F-01: Pierwszy Render deploy zielony

- **Wynik:** (fundament) Render service `habit-coach-ai` osiąga status `live` z Supabase Postgres (Supavisor pooler) jako backing DB; migracje Django built-ins zastosowane; `GET /admin/` zwraca formularz logowania z pełnym CSS.
- **Change ID:** `render-deploy-operational`
- **Odnośniki PRD:** `infrastructure.md` §Rekomendacja, `tech-stack.md` `deployment_target` (override do Render), `context/deployment/deploy-plan.md` Phase 5–6.
- **Odblokowuje:** S-01, S-02, S-03, S-04, S-05, S-06, S-07 — każdy slice weryfikuje się end-to-end przez Render deploy chain; bez zielonego F-01 żaden wycinek nie ma `ready` ścieżki weryfikacji.
- **Wymagania wstępne:** —
- **Równolegle z:** —
- **Blokady:** —
- **Niewiadome:** —
- **Ryzyko:** Pierwszy deploy obecnie pada na `DATABASE_URL` parser (direct connection 5432 zamiast Supavisor 6543 — patrz log Rendera). Naprawa to wymiana wartości env var na właściwy Transaction pooler URL z Supabase Dashboard. Po przejściu pierwszy deploy ustanawia działający łańcuch verify-by-deploy dla wszystkich kolejnych slice'ów.
- **Status:** done

## Wycinki

### S-01: Rejestracja i logowanie email+hasło

- **Wynik:** Niezalogowany odwiedzający rejestruje konto podając email i hasło, otrzymuje sesję (długa, „remember me" defaultem), i ląduje na empty-state dashboardu z instrukcją dodania pierwszego nawyku (US-01 AC: „po rejestracji użytkownik trafia bezpośrednio na ekran dodawania pierwszego nawyku").
- **Change ID:** `register-and-login`
- **Odnośniki PRD:** US-01, FR-001, FR-002.
- **Wymagania wstępne:** F-01.
- **Równolegle z:** —
- **Blokady:** —
- **Niewiadome:** —
- **Ryzyko:** Django built-in auth daje 80% pracy out-of-the-box; pułapką jest CSRF + ALLOWED_HOSTS pod onrender.com (już skonfigurowane w settings.py). Per-user isolation zaczyna się tutaj — wszystkie kolejne slice'y filtrują przez `request.user`.
- **Status:** done

### S-02: Zarządzanie nawykami (dodawanie, edycja, archiwizacja)

- **Wynik:** Zalogowany użytkownik dodaje nawyk z nazwą (codzienny tylko, częstotliwości złożone w Parked), edytuje nazwę istniejącego nawyku, archiwizuje nawyk (znika z list aktywnych, historia zachowana). Empty-state dashboardu kieruje go do dodania pierwszego nawyku.
- **Change ID:** `manage-habits`
- **Odnośniki PRD:** US-01, FR-005, FR-006, FR-007.
- **Wymagania wstępne:** S-01.
- **Równolegle z:** S-05 (po S-01), S-07 (po S-01).
- **Blokady:** —
- **Niewiadome:** —
- **Ryzyko:** Pierwszy project app — wymaga `uv run python manage.py startapp habits` + wpisania do INSTALLED_APPS + URL routing. Model `Habit` z polami `name`, `user (FK)`, `archived (bool)`, `created_at`. Archiwizacja przez `archived=True`, NIE `DELETE` (FR-007 — historia musi pozostać dla AI w S-04).
- **Status:** proposed

### S-03: Logowanie wykonania + widok historii 30 dni

- **Wynik:** Zalogowany użytkownik widzi listę swoich aktywnych nawyków z przyciskiem „wykonane dzisiaj" przy każdym; jedno kliknięcie loguje wykonanie z natychmiastowym potwierdzeniem wizualnym (NFR <200ms). Może cofnąć log tylko dla dnia dzisiejszego (wsteczne edycje zablokowane na poziomie domeny). Widok historii pokazuje siatkę 30 dni × każdy nawyk z oznaczeniem wykonane/niewykonane.
- **Change ID:** `log-execution-and-history`
- **Odnośniki PRD:** US-01, FR-008, FR-009, FR-010, NFR <200ms.
- **Wymagania wstępne:** S-02.
- **Równolegle z:** S-05, S-07.
- **Blokady:** —
- **Niewiadome:** —
- **Ryzyko:** Model `HabitExecution(habit FK, date, created_at)` z unikalnym indeksem `(habit, date)` żeby zapobiec duplikatom dziennym. Brak wstecznego logowania to constraint domeny (FR-009) — w views/serializatorach wymuszać `date == today()` przy create i delete. Latencja <200ms wymaga prostego endpointu (toggle bez full page reload, ewentualnie HTMX/lekki JS).
- **Status:** proposed

### S-04: Pierwsza ugruntowana rekomendacja AI (GWIAZDA PRZEWODNIA)

- **Wynik:** Zalogowany użytkownik z historią logowań (S-03) klika „Wygeneruj rekomendację", widzi pasek progresu / stan pośredni co najwyżej 2s (NFR), w ciągu 10s otrzymuje tekst AI cytujący jego konkretne nawyki, wzorce wykonań, słabsze dni, streaki lub przerwy. Ostatnia wygenerowana rekomendacja jest widoczna po powrocie do aplikacji (FR-012). Walidacja Primary Success Criterion: ≥ 75% rekomendacji odnosi się do konkretnych elementów danych (mierzone w S-06 lub osobno — patrz Q2 w Otwartych pytaniach).
- **Change ID:** `first-grounded-recommendation`
- **Odnośniki PRD:** US-01, FR-011, FR-012, NFR <10s + co najmniej co 2s progres.
- **Wymagania wstępne:** S-03 (rekomendacja wymaga historii do groundingu).
- **Równolegle z:** S-05, S-07.
- **Blokady:** OpenRouter API key musi być w Render env var `OPENROUTER_API_KEY` (konto utworzone per `infrastructure.md` §Phase 2; klucz wygenerowany).
- **Niewiadome:**
  - Wybór konkretnego modelu OpenRouter dla pierwszej rekomendacji (kandydaci z `infrastructure.md`: `anthropic/claude-haiku-4-5` lub `openai/gpt-4o-mini`). Owner: user. Blokuje: nie (pragmatyczny default w slice'ie, refine po pierwszych próbkach).
  - Kształt promptu zapewniający że ≥ 75% rekomendacji cytuje konkretne dane — pierwszy prompt zawiera nazwy nawyków + tabelę 30-dniowej historii i instrukcję „odnoś się do tych konkretnych nazw i wzorców". Iteracja w S-06 lub osobno. Owner: user. Blokuje: nie.
- **Ryzyko:** Główne miejsce gdzie hipoteza produktu się broni lub upada. Pierwsza wersja promptu z explicit grounding będzie prawdopodobnie wystarczająca dla MVP signal, ale samo prompt engineering to obszar wymagający iteracji. Latencja 10s NFR — OpenRouter z Haiku/gpt-4o-mini zmieści się w budżecie, ale streaming/intermediate UI dla NFR „progres co 2s" wymaga rozważenia (HTMX SSE lub server-sent events). Per-user isolation: zapytanie do OpenRouter MUSI zawierać tylko dane bieżącego `request.user`.
- **Status:** proposed

### S-05: Reset hasła przez email

- **Wynik:** Niezalogowany użytkownik z istniejącym kontem klika „Zapomniałem hasła", podaje email, otrzymuje link reset, klika link, ustawia nowe hasło, loguje się. Django built-in `PasswordResetView` + email service provider.
- **Change ID:** `password-reset-via-email`
- **Odnośniki PRD:** FR-003.
- **Wymagania wstępne:** S-01 (zarejestrowani użytkownicy do resetu).
- **Równolegle z:** S-02, S-03, S-04, S-07.
- **Blokady:** Email service provider (SMTP konto Gmail / Mailgun / SendGrid / Postmark / Resend) — musi być wybrany i skonfigurowany w Render env vars.
- **Niewiadome:**
  - Który email provider używamy? Pragmatyczne kandydaty: (a) Gmail SMTP z app password (najszybsze, ale rate-limited i nieprofesjonalne na produkcji), (b) Postmark / Resend (free tier do 100 emaili/dzień, transactional email focus, ~5 min konfiguracji), (c) Mailgun / SendGrid (większy free tier, więcej setup'u). Owner: user. Blokuje: **tak** — bez wybranego providera nie ma jak wysłać emaila i FR-003 jest hard-blocked.
- **Ryzyko:** Django built-in `PasswordResetView` + `EMAIL_BACKEND` w settings.py to mała ilość kodu, ale email deliverability może być problemem (SPF/DKIM, spam folders). Dla MVP pragmatyczny default to Resend (3000 free emails/mc, prostszy setup niż Mailgun).
- **Status:** blocked (Q4 z Block: tak)

### S-06: Automatyczna rekomendacja po przekroczeniu progu

- **Wynik:** Zalogowany użytkownik z historią logowań osiągającą próg (PRD wstępnie: ~7 dni dla co najmniej jednego nawyku, ale wymaga doprecyzowania) widzi proaktywną rekomendację AI bez konieczności klikania „Wygeneruj". Sprawdzenie progu odbywa się przy request time (per PRD Business Logic — NIE jako scheduled job).
- **Change ID:** `auto-recommendation-at-threshold`
- **Odnośniki PRD:** FR-013.
- **Wymagania wstępne:** S-04 (auto-trigger używa tej samej infrastruktury generacji rekomendacji).
- **Równolegle z:** S-05, S-07.
- **Blokady:** —
- **Niewiadome:**
  - Próg danych — ile dni logowań, dla ilu nawyków? (PRD §Open Questions Q1 — wstępnie ~7 dni dla ≥ 1 nawyku, ale dokładna definicja open). Owner: user. Blokuje: **tak**.
  - Częstotliwość auto-rekomendacji — jednorazowo po pierwszym osiągnięciu progu, czy cyklicznie co N dni? (PRD §Open Questions Q3). Owner: user. Blokuje: **tak**.
- **Ryzyko:** Logika progu i częstotliwości jest prosta technicznie, ale wymaga decyzji produktowych przed implementacją. Bez tych decyzji slice nie jest planowalny. Jednorazowo-po-progu jest pragmatycznym defaultem MVP per PRD §Open Questions Q3 resolution note.
- **Status:** blocked (Q1, Q3 z Block: tak)

### S-07: Wylogowanie

- **Wynik:** Zalogowany użytkownik klika „Wyloguj", sesja jest unieważniona, widzi ekran logowania. Django `LogoutView` z `next_page='/login/'`.
- **Change ID:** `logout`
- **Odnośniki PRD:** FR-004 (nice-to-have, demotowane w PRD — sesja sama wygasa).
- **Wymagania wstępne:** S-01.
- **Równolegle z:** S-02, S-03, S-04, S-05.
- **Blokady:** —
- **Niewiadome:** —
- **Ryzyko:** Mała ilość kodu (jeden URL + view + link w base template). Demotowane do nice-to-have w PRD, więc nie blokuje launchu — slot dostępny do dorobienia w dowolnym momencie po S-01.
- **Status:** proposed

## Przekazanie backlogu

| ID mapy drogowej | Change ID                              | Sugerowany tytuł problemu                                   | Gotowe do `/10x-plan` | Uwagi                                              |
| ---------------- | -------------------------------------- | ----------------------------------------------------------- | --------------------- | -------------------------------------------------- |
| F-01             | `render-deploy-operational`            | Naprawa pierwszego Render deploy + Supabase Postgres link   | yes                   | Aktualnie w toku — DATABASE_URL na port 6543.       |
| S-01             | `register-and-login`                   | Rejestracja konta i logowanie email+hasło                   | yes                   | Po zazielenieniu F-01.                              |
| S-02             | `manage-habits`                        | Dodawanie, edycja i archiwizacja nawyków                    | yes                   | Po S-01.                                            |
| S-03             | `log-execution-and-history`            | Logowanie wykonania + widok historii 30 dni                 | yes                   | Po S-02.                                            |
| S-04             | `first-grounded-recommendation`        | Pierwsza ugruntowana rekomendacja AI (gwiazda przewodnia)   | yes                   | Po S-03.                                            |
| S-05             | `password-reset-via-email`             | Reset zapomnianego hasła przez email                        | no                    | Zablokowane — wybór email providera.                |
| S-06             | `auto-recommendation-at-threshold`     | Proaktywna rekomendacja AI po przekroczeniu progu danych    | no                    | Zablokowane — próg + częstotliwość.                 |
| S-07             | `logout`                               | Jawne wylogowanie z aplikacji                               | yes                   | Nice-to-have, slot opcjonalny.                      |

## Otwarte pytania dotyczące mapy drogowej

1. **Próg danych dla automatycznej rekomendacji (FR-013) — ile dni logowań, dla ilu nawyków?** Owner: user. Blokuje: `S-06`. Pragmatyczny default MVP per PRD: ~7 dni dla ≥ 1 nawyku, ale wymaga doprecyzowania przed implementacją S-06.
2. **Sposób pomiaru kryterium „≥ 75% rekomendacji odnosi się do konkretnych danych użytkownika".** Owner: user. Blokuje: roadmap-wide — bez metody pomiaru Primary Success Criterion nie jest weryfikowalne, nawet po wdrożeniu S-04. Opcje: manualny przegląd próbki (najtaniej dla MVP), automatyczna detekcja tokenów-z-danych w odpowiedzi (wymaga reguły), kombinacja. Praktycznie potrzebne przed launch'em S-04 dla mierzalnego sygnału, ale nie blokuje samej implementacji wycinka.
3. **Częstotliwość automatycznej rekomendacji (FR-013) — jednorazowo po progu czy cyklicznie?** Owner: user. Blokuje: `S-06`. Pragmatyczny default MVP per PRD: jednorazowo po pierwszym przekroczeniu progu; cykliczność doprecyzowana w v1.x.
4. **Email service provider dla password reset (FR-003).** Owner: user. Blokuje: `S-05`. Kandydaci: Resend (zalecane na MVP — 3000 emaili/mc free, ~5 min setup), Postmark, Mailgun, SendGrid, Gmail SMTP (najszybsze ale unprofessional).

## Zaparkowane

- **Powiadomienia push i email** (PRD §Non-Goals) — logowanie nawyków zależy wyłącznie od inicjatywy użytkownika; brak wieczornych przypomnień w MVP.
- **Integracje z platformami fitness/health** (PRD §Non-Goals) — brak automatycznego logowania snu/treningu z trackerów/smartwatchy/aplikacji zdrowotnych.
- **Gamifikacja** (PRD §Non-Goals) — brak punktów/odznak/rankingów/poziomów; widok własnej historii to jedyna „nagroda".
- **Aplikacje mobilne natywne** (PRD §Non-Goals) — MVP tylko web; natywne odłożone.
- **Współdzielenie nawyków między użytkownikami** (PRD §Non-Goals) — produkt single-user, brak link-share/team-workspaces/publicznych profili.
- **Częstotliwości nawyków inne niż codzienna** (PRD §Non-Goals) — wszystkie nawyki w MVP codzienne; „N razy w tygodniu" / „tylko dni robocze" odłożone do v2.
- **Historia wygenerowanych rekomendacji w UI** (PRD §Non-Goals) — użytkownik widzi tylko ostatnią; archiwum rekomendacji odłożone.
- **Logowanie wykonań wstecz + cofanie wstecz poza dniem bieżącym** (PRD §Non-Goals, FR-009) — egzekwowane jako constraint domeny; streaki muszą pozostać realne.
- **Hard delete nawyku wraz z historią** (PRD §Non-Goals, FR-007) — w MVP tylko archiwizacja zachowująca historię dla AI.
- **Wielo-regionalne HA / production-scale architecture** (`infrastructure.md` §Poza zakresem) — Render single-region Frankfurt do MVP; multi-region/DR po PMF.
- **CI/CD via GitHub Actions** (`infrastructure.md` §Poza zakresem) — natywna Render Git integration realizuje auto-deploy-on-merge; explicit Actions workflow tylko jeśli pojawi się potrzeba.
- **Monitoring i error tracking (Sentry/BetterStack)** (`infrastructure.md` §Poza zakresem) — odłożone do prawdziwego ruchu użytkowników.

## Zrobione

- **F-01: Pierwszy Render deploy zielony** — Operacyjny od 2026-06-07; weryfikacja w `context/deployment/deploy-plan.md`. Lekcja: —.
- **S-01: Rejestracja i logowanie email+hasło** — Zarchiwizowano 2026-06-04 → `context/archive/2026-06-04-register-and-login/`. Retro 2026-06-07 → `context/archive/2026-06-07-register-and-login-retro/`. Lekcja: success-criteria sign-off must actually read the command output (`context/foundation/lessons.md`).
