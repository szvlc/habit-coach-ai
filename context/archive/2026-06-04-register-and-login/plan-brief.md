# Register and login — krótki plan

> Pełny plan: `context/changes/register-and-login/plan.md`
> Mapa drogowa: `context/foundation/roadmap.md` § S-01

## Co i dlaczego

Pierwszy wycinek z mapy drogowej (S-01) wprowadzający email+hasło uwierzytelnianie z długą sesją i empty-state dashboard, na którym użytkownik ląduje po rejestracji. Dostarcza FR-001 (rejestracja), FR-002 (logowanie z remember-me), oraz US-01 AC dotyczący onboarding flow. Pełni rolę enabler'a per-user isolation — wszystkie kolejne slice'y (S-02 habits, S-03 logging, S-04 AI rec) będą filtrować `request.user`.

## Punkt wyjścia

Django 6.0 scaffold z `habit_coach_ai/` jako project package; `INSTALLED_APPS` = tylko Django built-ins; brak project apps, templates, URLs poza `/admin/`; `LANGUAGE_CODE = "en-us"`; `db.sqlite3` ma już zastosowane built-in migracje (z lokalnego smoke testu); F-01 production deploy w toku (nadal naprawiany DATABASE_URL na Supavisor pooler — Supabase Postgres jeszcze bez żadnych migracji).

## Pożądany stan końcowy

Niezalogowany → `/register/` → wypełnia email+hasło → auto-login → `/` z empty-state CTA „Dodaj swój pierwszy nawyk". Niezalogowany → `/accounts/login/` → email+hasło → 30-dniowa sesja → `/`. Django admin używa email zamiast username. Polskie komunikaty walidacji. Tailwind CSS styling. 6 testów Django zielone. Production deploy zielony i happy path działa na `https://habit-coach-ai.onrender.com/`.

## Kluczowe podjęte decyzje

| Decyzja | Wybór | Dlaczego (1 zdanie) | Źródło |
| --- | --- | --- | --- |
| Zakres wycinka | FR-001 + FR-002 + US-01 AC; FR-003 i FR-004 osobno | Roadmap rozdzielił password reset (S-05, blocked) i logout (S-07, nice-to-have); S-01 = onboarding na ścieżce do gwiazdy przewodniej | Roadmap |
| User model | Custom `accounts.User` extending `AbstractUser`, `USERNAME_FIELD='email'`, `username=None` | PRD wymaga email-as-identifier; native Django pattern; decyzja musi być PRZED pierwszą migracją | Plan |
| Struktura aplikacji | Dedykowana app `accounts/` (nie w `habit_coach_ai/`) | Django convention; separation of concerns; project package zostaje czysto konfiguracyjny | Plan |
| Auth views | Django built-in `LoginView`/`LogoutView` + custom `RegisterView` (CreateView z auto-login) | Maksymalnie wykorzystuje Django (CSRF, session, password validators built-in); register custom bo Django nie ma built-in | Plan |
| Template + CSS | Tailwind CSS via CDN, project-level `templates/` directory | Zero build step (server-rendered Django); profesjonalny look od razu; ogromna baza wiedzy agentów | Plan |
| Sesja / remember-me | `SESSION_COOKIE_AGE = 30 * 24 * 3600`, brak checkboxa | PRD mówi „długa sesja domyślnie"; brak wyboru = właściwa semantyka | Plan |
| Post-register flow | Placeholder dashboard view z empty-state CTA linkującym do `# TODO: S-02` | PRD US-01 AC wprost wymaga empty-state „dodaj pierwszy nawyk"; daje S-02 punkt zaczepienia | Plan + PRD AC |
| Język UI | `LANGUAGE_CODE = "pl"` (zmiana z "en-us") | PRD jest po polsku → Django form validation messages też | Plan |

## Zakres

**W zakresie:**
- Custom User model z email; admin obsługa
- Register view z auto-login po save
- Built-in login/logout views (z `django.contrib.auth.urls` include)
- Dashboard view (LoginRequiredMixin) z empty-state CTA
- Templates: `base.html` (Tailwind), `registration/login.html`, `registration/register.html`, `dashboard.html`
- Settings: AUTH_USER_MODEL, LANGUAGE_CODE='pl', SESSION_COOKIE_AGE, LOGIN_*, TEMPLATES['DIRS']
- 6 testów Django (register happy, register collision, register weak password, login happy, login fail, dashboard requires login)
- Push do GitHub + production smoke test

**Poza zakresem:**
- Password reset (FR-003 → S-05, blocked na email provider)
- Logout link w UI (FR-004 → S-07, nice-to-have)
- Habit CRUD (S-02)
- Social auth / OAuth
- Email confirmation przy rejestracji
- Profile / user settings
- API endpoints (server-rendered HTML wystarcza)

## Architektura / Podejście

Server-rendered Django: project package `habit_coach_ai/` zostaje konfiguracją; nowa app `accounts/` zawiera models/views/forms/urls/templates/admin/tests. URL routing: `/admin/` (Django admin), `/accounts/*` (Django built-in auth URLs przez include), `/register/` i `/` (accounts.urls). Single Tailwind CDN script w `base.html` pokrywa wszystkie templates. Session storage: domyślny database-backed session via `accounts_user` + `django_session`. CSRF + ALLOWED_HOSTS — już skonfigurowane w settings.py z poprzednich faz deploy plan.

## Fazy w skrócie

| Faza | Co dostarcza | Kluczowe ryzyko |
| --- | --- | --- |
| 1. User model + accounts app + settings | Custom User w DB, AUTH_USER_MODEL ustawione, admin operuje na email | Trzeba nuke `db.sqlite3` (lokalne built-in migracje konfliktują z custom User); prod Supabase fresh, więc bezpieczne |
| 2. Auth views + URL wiring | `/register/`, `/login/`, `/logout/` i `/` odpowiadają HTML (bez stylowania jeszcze) | Wszystkie URLs muszą się resolvować zanim templates mają sens; ImportError'y wyłapie `check` |
| 3. Templates + Tailwind + Dashboard | Pełen happy path renderuje z Tailwind, polskie komunikaty, empty-state CTA | `templates/registration/login.html` hardcoded path Django LoginView; pomyłka w nazwie folderu = 500 |
| 4. Tests + production deploy weryfikacja | 6 testów zielone, prod deploy zielony, register+login działa na live URL | F-01 musi być uprzednio zazielenione (obecnie w toku); na Supabase `accounts.0001_initial` musi czysto wjechać |

**Wymagania wstępne:** F-01 (`render-deploy-operational`) zielony — pierwszy Render deploy musi działać przed Phase 4 push. Konto Supabase z poprawnym Supavisor pooler URL w `DATABASE_URL` env var na Render. GitHub repo `szvlc/habit-coach-ai` (już istnieje, prywatne).

**Szacowany nakład pracy:** ~3-4 sesje implementacyjne, jeden agent (`/10x-implement register-and-login phase N` per faza). Phase 1+2 są mechaniczne; Phase 3 to najwięcej pracy ze stylingiem; Phase 4 to testy + push + smoke.

## Otwarte ryzyka i założenia

- **F-01 deploy jeszcze nie zielony** — Phase 4 push triggeruje Render deploy, który zadziała tylko jeśli DATABASE_URL config jest poprawny (Supavisor pooler port 6543, nie direct 5432). Jeśli F-01 nadal jest broken w momencie Phase 4 — zatrzymaj się, dokończ F-01, wróć.
- **Tailwind CDN payload ~50KB per cold hit** — akceptowalne dla MVP; long-term: Tailwind CLI build w `collectstatic` (poza scope).
- **`db.sqlite3` lokalnie ma builtin migracje** — pierwsza migracja `accounts` wymaga `rm db.sqlite3` lokalnie; lokalne dane testowe znikną (mamy tylko superuser z F-01 smoke testu, którego można odtworzyć).
- **Hard rule per-user isolation** — w S-01 nie ma jeszcze user-specific data (S-02+), ale `LoginRequiredMixin` na `DashboardView` to pierwszy punkt egzekwowania.
- **`LANGUAGE_CODE='pl'` wpływa też na admin** — admin będzie po polsku, co może zmylić jeśli ktoś jest przyzwyczajony do EN. Akceptowalne — PRD jest po polsku, więc cała aplikacja per consistency.

## Kryteria sukcesu (podsumowanie)

- Lokalnie: `manage.py test accounts` — 6 zielonych testów.
- Lokalnie: pełny flow `/` (redirect login) → `/register/` (utwórz konto) → auto-login → `/` (dashboard z CTA) renderuje z Tailwind styling i polskim językiem.
- Production: deploy zielony, ten sam flow działa na `https://habit-coach-ai.onrender.com/`, Supabase `accounts_user` ma wpis.
