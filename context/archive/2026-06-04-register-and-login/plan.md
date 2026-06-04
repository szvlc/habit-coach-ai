# Register and login — plan implementacji

## Przegląd

Pierwszy wycinek z mapy drogowej (S-01 `register-and-login`). Wprowadza email+hasło uwierzytelnianie z długą sesją (30 dni defaultem) i empty-state dashboard, na którym użytkownik ląduje po rejestracji. Dostarcza FR-001 (rejestracja), FR-002 (logowanie z remember-me), oraz US-01 AC (po rejestracji landing na ekranie dodawania pierwszego nawyku). FR-003 (password reset) i FR-004 (logout) są w osobnych slice'ach (S-05, S-07) i nie są w zakresie tego planu.

Pełni rolę enabler'a dla całego per-user isolation łańcucha — wszystkie kolejne slice'y (S-02 habits, S-03 logging, S-04 AI rec) filtrują `request.user`.

## Analiza stanu obecnego

Z `## Baseline` w `@context/foundation/roadmap.md` (2026-05-30) + bezpośredniej inspekcji `habit_coach_ai/settings.py`:

- Django 6.0 scaffold, `INSTALLED_APPS = [..., django.contrib.admin, auth, contenttypes, sessions, messages, staticfiles]` — tylko built-ins (`habit_coach_ai/settings.py:35-42`).
- `django.contrib.auth` zarejestrowane → built-in `User` model + `AUTH_PASSWORD_VALIDATORS` aktywne (`habit_coach_ai/settings.py:86-99`).
- Brak project apps; brak project templates; brak project URLs poza `admin/` (`habit_coach_ai/urls.py`).
- `LANGUAGE_CODE = 'en-us'`, `TIME_ZONE = 'UTC'`, `USE_TZ = True` (`habit_coach_ai/settings.py:105-111`).
- `db.sqlite3` lokalnie z zastosowanymi Django built-in migracjami (z lokalnego smoke testu — patrz `context/deployment/deploy-plan.md` Phase 1.4).
- F-01 (pierwszy Render deploy) nadal jest w toku (kończony przez DATABASE_URL fix na Supavisor pooler port 6543); migracje na Supabase Postgres NIE zostały jeszcze zastosowane.
- WhiteNoise + Tailwind via CDN nie wymagają build step — pasują do server-rendered HTML server-side Django.
- AGENTS.md hard rule: per-user isolation — każdy view/queryset filtruje `request.user`.

## Pożądany stan końcowy

Po wdrożeniu Phase 1-4:

- Niezalogowany odwiedzający na `/register/` → wypełnia email + password (+ confirm) → submit → konto utworzone z `accounts.User`, auto-login, redirect do `/`.
- Niezalogowany odwiedzający na `/login/` (lub przekierowany z gated route) → wypełnia email + password → submit → sesja utworzona z TTL 30 dni → redirect do `/`.
- `/` (root) → jeśli zalogowany: `DashboardView` z empty-state CTA „Dodaj swój pierwszy nawyk"; jeśli niezalogowany: redirect do `/login/`.
- Django admin używa email zamiast username; `createsuperuser` prosi o email + password.
- Polskie komunikaty walidacji form (`LANGUAGE_CODE='pl'`).
- Pełny styling Tailwind CSS na wszystkich stronach (login, register, dashboard).
- 6 testów Django w `accounts/tests.py` przechodzi zielono.
- Production Render deploy zielony, register+login działa na `https://habit-coach-ai.onrender.com/`.

### Kluczowe odkrycia

- **Custom User model musi być zadeklarowany PRZED pierwszą migracją** — Django nie pozwala swap'ować User modelu po migracji (`habit_coach_ai/settings.py` — brak `AUTH_USER_MODEL` obecnie oznacza default `auth.User`). Lokalne `db.sqlite3` ma już zastosowane built-in migracje → wymaga `rm db.sqlite3` przed pierwszym `makemigrations accounts`. Production Supabase jest fresh, więc tam bez ryzyka.
- **`django.contrib.auth.urls`** include daje za darmo: `/login/`, `/logout/`, `/password_change/`, `/password_change_done/`, `/password_reset/`, `/password_reset_done/`, `/reset/<uidb64>/<token>/`, `/reset/done/`. Plan używa tylko login/logout w S-01; password_reset użyje S-05.
- **Templates location**: `templates/registration/login.html` jest hardcoded w `LoginView.template_name` → musi istnieć dokładnie pod tą ścieżką dla built-in. Reszta templates w `templates/` przez `TEMPLATES['DIRS']`.
- **CSRF + ALLOWED_HOSTS** już skonfigurowane — `settings.py` ma `ALLOWED_HOSTS` z env var `.onrender.com` + localhost w debug. Brak dodatkowych zmian.
- **`form_valid` w `RegisterView`** musi wywołać `login(self.request, self.object)` po `super().form_valid(form)` — Django nie auto-loguje po `CreateView.save()`.

## Czego NIE robimy

- **Password reset** (FR-003) — slice S-05, blocked na decyzji email-providera (Q4 z roadmap.md).
- **Logout endpoint w UI** (FR-004) — slice S-07, nice-to-have. `django.contrib.auth.urls` include daje `/logout/` URL, ale nie dodajemy linka w base.html w tym slice.
- **Social auth / OAuth providers** — poza zakresem PRD, parked.
- **Email confirmation** — PRD nie wymaga.
- **Custom password policy** — Django default `AUTH_PASSWORD_VALIDATORS` wystarcza (min 8 chars, common-password check, similarity check, numeric check).
- **Profile / user settings** — poza S-01, nie ma user story.
- **Habit CRUD** — slice S-02, kolejny.
- **API endpoints / DRF** — server-rendered HTML wystarcza per tech-stack decyzja.

## Podejście do implementacji

Czterofazowy plan, każda faza ma jasny gate weryfikacji. Phase 1 ustawia foundation (custom User + settings), Phase 2 dodaje views + URLs (działają choć bez styling), Phase 3 dorzuca templates + Tailwind + dashboard, Phase 4 weryfikuje testami i prod deploy. Sekwencja jest topologiczna — Phase 1 fail blokuje Phase 2; Phase 3 zależy od Phase 2 URLs.

Każda faza kończy się manual gate: dev confirm że auto-verification przeszło + ręczny test (uv run python manage.py runserver + browser smoke). To zgodne z `/10x-implement` workflow z lekcji M2L2.

## Krytyczne szczegóły implementacji

- **Sekwencjonowanie migracji custom User**: `AUTH_USER_MODEL = 'accounts.User'` musi być ustawione w `habit_coach_ai/settings.py` PRZED pierwszym `makemigrations accounts`. Lokalne `db.sqlite3` ma już zastosowane Django built-in migracje (które wbudowały referencje do default `auth.User`), więc trzeba `rm db.sqlite3` przed migracją. Na production Supabase (fresh, deploy nigdy nie skończył) ten problem nie wystąpi.

## Faza 1: User model + accounts app + settings hardening

### Przegląd

Stwórz `accounts/` app z custom User model (email jako USERNAME_FIELD), zarejestruj w settings, nuke lokalną sqlite, wygeneruj i zastosuj migrację. Po tej fazie Django wie o nowym User modelu, `createsuperuser` prosi o email, admin pokazuje email zamiast username.

### Wymagane zmiany

#### 1. Utwórz aplikację `accounts/`

**Plik**: (powstanie cały katalog `accounts/`)

**Cel**: Zapewnić dedykowaną przestrzeń dla User modelu i auth-related views per Django convention. Konwencjonalne `startapp` daje migrations/, admin.py, apps.py, models.py, tests.py, views.py.

**Kontrakt**: `uv run python manage.py startapp accounts` w cwd. Powstaje `accounts/__init__.py`, `accounts/admin.py`, `accounts/apps.py`, `accounts/migrations/__init__.py`, `accounts/models.py`, `accounts/tests.py`, `accounts/views.py`.

#### 2. Custom User model

**Plik**: `accounts/models.py`

**Cel**: Email jako unikalny identyfikator logowania (per FR-001 i FR-002), bez pola `username`. Reszta pól z `AbstractUser` (password, is_active, is_staff, is_superuser, date_joined, last_login).

**Kontrakt**: Klasa `User(AbstractUser)` z `username = None`, `email = EmailField(unique=True)`, `USERNAME_FIELD = 'email'`, `REQUIRED_FIELDS = []` (bo email JEST USERNAME_FIELD, więc nie dodaje się go do REQUIRED). `__str__` zwraca `self.email`.

#### 3. Custom UserAdmin

**Plik**: `accounts/admin.py`

**Cel**: Django admin nie wie z marszu, że `username` nie istnieje — domyślny `UserAdmin` próbuje pokazywać pole `username` i pada. Rejestrujemy custom subclass.

**Kontrakt**: `@admin.register(User)` z `CustomUserAdmin(UserAdmin)` definiującym `ordering = ('email',)`, `list_display = ('email', 'is_staff', 'is_active', 'date_joined')`, `fieldsets` i `add_fieldsets` używające `email` zamiast `username`, `search_fields = ('email',)`.

#### 4. Settings — dodaj accounts + AUTH_USER_MODEL + i18n + sesja + auth URLs

**Plik**: `habit_coach_ai/settings.py`

**Cel**: Zarejestrować accounts app, wskazać Django na custom User model, zmienić język na polski (komunikaty walidacji + Django admin), ustawić długą sesję 30 dni, skonfigurować login redirect URLs, dodać templates directory.

**Kontrakt**:
- `INSTALLED_APPS` rozszerzone o `"accounts"`.
- Dodać `AUTH_USER_MODEL = "accounts.User"` (przed pierwszą migracją projektu — krytyczne).
- `LANGUAGE_CODE = "pl"` (zamiast `"en-us"`).
- `SESSION_COOKIE_AGE = 30 * 24 * 60 * 60` (30 dni w sekundach).
- `LOGIN_URL = "login"`, `LOGIN_REDIRECT_URL = "accounts:dashboard"`, `LOGOUT_REDIRECT_URL = "login"`.
- `TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]` (project-level templates dir).

#### 5. Nuke lokalną sqlite + wygeneruj i zastosuj migracje

**Plik**: `db.sqlite3` (usunięcie) i `accounts/migrations/0001_initial.py` (wygenerowanie)

**Cel**: Lokalne db.sqlite3 ma zastosowane built-in migracje z default `auth.User` jako podstawą. Po wprowadzeniu custom User Django wymaga fresh migracji.

**Kontrakt**: Sekwencja: `rm db.sqlite3` → `uv run python manage.py makemigrations accounts` → `uv run python manage.py migrate`. Wygenerowana migracja `accounts/0001_initial.py` powinna referować `AUTH_USER_MODEL` i tworzyć tabelę `accounts_user` z polami email (unique), password, is_active, is_staff, is_superuser, last_login, date_joined.

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py check` przechodzi bez warnings
- `uv run python manage.py makemigrations --check accounts` zwraca "No changes detected" (po wygenerowaniu migracji)
- `uv run python manage.py migrate` przechodzi
- `accounts_user` tabela istnieje w db.sqlite3 (sprawdź: `uv run python -c "import sqlite3; print(sqlite3.connect('db.sqlite3').execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall())"`)

#### Weryfikacja ręczna

- `uv run python manage.py createsuperuser` prosi o **email** (nie username), tworzy konto
- `uv run python manage.py runserver` startuje bez błędu
- `http://127.0.0.1:8000/admin/` — login po emailu działa, admin pokazuje "Users" z kolumną email

**Uwaga implementacyjna**: Po pomyślnym przejściu weryfikacji automatycznej, zatrzymaj się tutaj na ręczne potwierdzenie, że createsuperuser + admin login działają, zanim przejdziesz do Phase 2.

---

## Faza 2: Auth views + URL wiring

### Przegląd

Dodaj custom `RegisterView` (CreateView z auto-login po save) + placeholder `DashboardView`, podłącz Django built-in auth URLs (`/login/`, `/logout/` etc.) + accounts URLs. Po tej fazie URLs odpowiadają HTML-em (bez stylowania).

### Wymagane zmiany

#### 1. Custom UserCreationForm

**Plik**: `accounts/forms.py` (nowy)

**Cel**: Default `UserCreationForm` Django operuje na polu `username`. Custom subclass mówi formularzowi: pracujesz na polu `email` z `accounts.User`.

**Kontrakt**: `CustomUserCreationForm(UserCreationForm)` z `class Meta: model = User; fields = ("email",)`. Pola `password1` i `password2` dziedziczone z `UserCreationForm` automatycznie.

#### 2. RegisterView (z auto-login) + DashboardView (placeholder)

**Plik**: `accounts/views.py`

**Cel**: `RegisterView` używa Django `CreateView` z naszym `CustomUserCreationForm`, po pomyślnym zapisie automatycznie loguje użytkownika i redirectuje na dashboard (per US-01 AC). `DashboardView` to `LoginRequiredMixin + TemplateView` renderujący `dashboard.html` z empty-state CTA — niezalogowany odwiedzający dostaje redirect do LOGIN_URL.

**Kontrakt**:
- `RegisterView(CreateView)` z `form_class = CustomUserCreationForm`, `template_name = "registration/register.html"`, `success_url = reverse_lazy("accounts:dashboard")`, override'em `form_valid` który po `super().form_valid(form)` wywołuje `login(self.request, self.object)` i zwraca response.
- `DashboardView(LoginRequiredMixin, TemplateView)` z `template_name = "dashboard.html"`.

#### 3. accounts/urls.py

**Plik**: `accounts/urls.py` (nowy)

**Cel**: Wystawić register i dashboard URLs pod namespace `accounts`.

**Kontrakt**: `app_name = "accounts"`, `urlpatterns = [path("register/", views.RegisterView.as_view(), name="register"), path("", views.DashboardView.as_view(), name="dashboard")]`.

#### 4. Include accounts + auth URLs w project urls.py

**Plik**: `habit_coach_ai/urls.py`

**Cel**: Wystawić `/admin/`, Django built-in auth URLs (login, logout, password reset etc.), i nasze accounts URLs (register, dashboard).

**Kontrakt**:
- `path("admin/", admin.site.urls)`
- `path("accounts/", include("django.contrib.auth.urls"))` (daje `/accounts/login/`, `/accounts/logout/`, `/accounts/password_*/`)
- `path("", include("accounts.urls"))` (root = dashboard, `/register/` = register)

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py check` przechodzi
- `uv run python manage.py show_urls 2>/dev/null` lub `uv run python -c "from django.urls import get_resolver; ..." ` listuje endpointy: `/`, `/register/`, `/accounts/login/`, `/accounts/logout/`
- Wszystkie ImportError/ModuleNotFoundError są nieobecne (przejście check'a to wystarczy)

#### Weryfikacja ręczna

- `http://127.0.0.1:8000/register/` zwraca HTML (nie 404, nie 500 — może być nieostylowane)
- `http://127.0.0.1:8000/accounts/login/` zwraca HTML (Django default template — wymaga templates w Phase 3 dla pełnego renderu, ale URL resolve OK)
- `http://127.0.0.1:8000/` (niezalogowany) redirectuje do `/accounts/login/?next=/`
- `http://127.0.0.1:8000/` (zalogowany jako superuser z Phase 1) zwraca HTML dashboard (template missing OK — Phase 3)

**Uwaga implementacyjna**: Po pomyślnej weryfikacji automatycznej, ręcznie potwierdź że URLs odpowiadają (nawet jeśli HTML jeszcze nieostylowany — to Phase 3), zanim przejdziesz do Phase 3.

---

## Faza 3: Templates + Tailwind + Dashboard placeholder

### Przegląd

Dodaj `base.html` z Tailwind CDN, `registration/login.html`, `registration/register.html`, `dashboard.html` z empty-state CTA. Po tej fazie pełen happy path (visit → register → auto-login → dashboard) renderuje się z profesjonalnym Tailwind styling.

### Wymagane zmiany

#### 1. Base template z Tailwind CDN

**Plik**: `templates/base.html` (nowy)

**Cel**: Wspólny szablon dla wszystkich auth stron + dashboard. Tailwind CDN przez `<script src="https://cdn.tailwindcss.com"></script>` daje cały framework bez build step. Blocki `{% block title %}` i `{% block content %}` używane przez child templates.

**Kontrakt**: HTML5 doctype, `<html lang="pl">`, `<head>` z meta charset + viewport + title block + Tailwind CDN script, `<body>` z content block. Minimalistyczna nawigacja (np. nazwa aplikacji w h1) lub bez — child templates same kontrolują layout. Czy to jest container? Standardowy max-w-md mx-auto pt-8 wystarczy dla auth forms.

#### 2. Login template

**Plik**: `templates/registration/login.html` (nowy — ścieżka hardcoded w Django LoginView)

**Cel**: Renderować login form (email + password) z Tailwind styling. Django `LoginView` automatycznie przekazuje context z `form` (instance `AuthenticationForm`).

**Kontrakt**: Extends `base.html`, content block z `<form method="post">` zawierającym `{% csrf_token %}`, `{{ form.as_p }}` (lub manualne renderowanie pól dla lepszego stylingu — preferowane), submit button. Link „Nie masz konta? Zarejestruj się" do `{% url 'accounts:register' %}`. Komunikaty błędów (`{{ form.errors }}`) widoczne.

#### 3. Register template

**Plik**: `templates/registration/register.html` (nowy)

**Cel**: Renderować register form (email + password1 + password2). Polskie etykiety walidacji dziedziczone z Django (gdy `LANGUAGE_CODE='pl'`).

**Kontrakt**: Extends `base.html`, content block z `<form method="post">` z `{% csrf_token %}`, render pól z `CustomUserCreationForm`, submit button. Link „Masz już konto? Zaloguj się" do `{% url 'login' %}` (Django built-in name).

#### 4. Dashboard template (empty-state CTA)

**Plik**: `templates/dashboard.html` (nowy)

**Cel**: Spełnia PRD US-01 AC: po rejestracji użytkownik widzi instrukcję dodania pierwszego nawyku. Pusta lista nawyków + jeden duży button CTA „Dodaj swój pierwszy nawyk" → link do placeholdera `# TODO: S-02 wire /habits/add/`.

**Kontrakt**: Extends `base.html`, content block z `<h1>Witaj, {{ user.email }}</h1>`, paragraph „Nie masz jeszcze żadnych nawyków", CTA button (`<a href="#" class="...">Dodaj swój pierwszy nawyk</a>` z komentarzem HTML `<!-- TODO: S-02 — point href to {% url 'habits:add' %} -->`). Brak link do logout (FR-004 nice-to-have, S-07).

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py check` przechodzi bez `template does not exist` warnings dla `registration/login.html` (Django built-in LoginView może wyemitować ostrzeżenie podczas startup'u, jeśli template missing)
- `uv run python manage.py collectstatic --no-input --dry-run` przechodzi bez błędów (Tailwind via CDN, nie ma collectstatic dla CSS w tym slice — sprawdzenie tylko że settings nadal się parsują)

#### Weryfikacja ręczna

- `http://127.0.0.1:8000/accounts/login/` — login form renderuje z pełnym Tailwind styling, polskie etykiety
- `http://127.0.0.1:8000/register/` — register form renderuje z pełnym Tailwind styling, polskie etykiety
- Wpisanie złego email format w register → polski komunikat błędu („Wprowadź poprawny adres email" lub podobny — Django pl translation)
- Rejestracja: wpisz email + password (2x) → submit → auto-login → redirect do `/` → dashboard renderuje z empty-state CTA „Dodaj swój pierwszy nawyk"
- Logout via dashboard nie istnieje (FR-004 w S-07) — to OK, ale `http://127.0.0.1:8000/accounts/logout/` (direct URL) działa i redirectuje do login (LOGOUT_REDIRECT_URL)
- Re-login z poprzednio utworzonego konta działa

**Uwaga implementacyjna**: Po automatycznej i ręcznej weryfikacji, zatrzymaj się na confirm że pełny happy path działa lokalnie zanim przejdziesz do Phase 4 (testy + prod deploy).

---

## Faza 4: Tests + production deploy weryfikacja

### Przegląd

Napisz Django unit testy dla auth flows (5-6 testów), push do GitHub, Render auto-deploys, smoke test na live URL. Po tej fazie S-01 jest na produkcji i FR-001 + FR-002 zweryfikowane end-to-end.

### Wymagane zmiany

#### 1. Tests

**Plik**: `accounts/tests.py`

**Cel**: Zweryfikować 6 ścieżek krytycznych dla FR-001, FR-002 i per-user-isolation hard rule. Django `TestCase` (transactional) z `Client()`.

**Kontrakt**: Klasa `AccountsTests(TestCase)` z metodami:
- `test_register_creates_user_and_logs_in`: POST `/register/` z valid email+pass → 302 do `/`, `User.objects.filter(email=...).exists()` True, response.wsgi_request.user.is_authenticated True.
- `test_register_rejects_duplicate_email`: utwórz user, POST `/register/` z tym samym emailem → 200 (form re-renders), error w form.errors, only 1 user w DB.
- `test_register_rejects_weak_password`: POST z `password='123'` → 200 + error (Django password validator).
- `test_login_with_correct_password`: utwórz user, POST `/accounts/login/` z valid creds → 302 do `/`, sesja authenticated.
- `test_login_with_wrong_password`: utwórz user, POST `/accounts/login/` ze złym password → 200 (form re-renders), user nie zalogowany.
- `test_dashboard_requires_login`: GET `/` niezalogowany → 302 do `/accounts/login/?next=/`.

#### 2. Commit + push

**Plik**: (nie plik — git operation)

**Cel**: Push triggeruje Render auto-deploy. Migracja `accounts/0001_initial.py` zostanie zastosowana na Supabase Postgres przez `preDeployCommand` w `render.yaml`.

**Kontrakt**: `git add accounts/ habit_coach_ai/settings.py habit_coach_ai/urls.py templates/` + (potencjalnie) usunięcie `db.sqlite3` z indexu jeśli był śledzony (powinien być w .gitignore) + commit message zgodny z konwencją + `git push origin main`.

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py test accounts` — wszystkie 6 testów zielone
- Lokalny `uv run python manage.py check --deploy` — brak critical warnings (poza tym że SECRET_KEY jest env var, co jest OK)
- Render deploy: po push, log Render pokazuje `Applying accounts.0001_initial... OK` w preDeployCommand fazie + `gunicorn` startuje + service status `live`

#### Weryfikacja ręczna

- `https://habit-coach-ai.onrender.com/accounts/login/` — Tailwind styling renderuje, polski język
- `https://habit-coach-ai.onrender.com/register/` — utworzenie nowego konta, auto-login, redirect do `/` z dashboard
- Logout (via direct URL `/accounts/logout/`) → redirect do login
- Re-login z istniejącym kontem → dashboard
- Supabase dashboard → Tables → `accounts_user` istnieje z wpisem (lub kilku) z poprawnym emailem
- Render Logs nie pokazują 5xx errors po test scenariuszu

**Uwaga implementacyjna**: Po zazielenieniu prod deploy + smoke testu z prawdziwego URL, możemy uznać S-01 za completed i przekazać do `/10x-archive register-and-login`. To zaktualizuje roadmap.md (`S-01 Status: done` + wpis w `## Done`).

---

## Strategia testowania

### Testy jednostkowe

- 6 testów w `accounts/tests.py` jak opisano w Phase 4 — cover register happy path, register collision, register weak password, login happy, login fail, dashboard auth required.
- Brak per-method docstring — nazwy testów są self-documenting.
- Brak fixture'ów per test (każdy tworzy User w setUp lub inline) — small slice, dziel-i-rządź.

### Testy integracyjne

- Pełen flow register → auto-login → dashboard pokryty przez `test_register_creates_user_and_logs_in` (sprawdza response chain: 302 + session).
- Brak osobnych testów integracyjnych — Phase 4 unit testy są wystarczające dla MVP, prod smoke test (manual) potwierdza end-to-end.

### Kroki testowania ręcznego

1. Lokalnie: `uv run python manage.py runserver` → odwiedź `/`, zostań przekierowany do `/accounts/login/`, kliknij „Zarejestruj się", wypełnij email + hasło (2x), submit → powinieneś wylądować na dashboard z CTA.
2. Lokalnie: spróbuj zarejestrować z tym samym emailem 2 razy — drugi raz powinien pokazać błąd, nie 500.
3. Lokalnie: spróbuj zarejestrować ze słabym hasłem `123` — Django password validator powinien blokować z polskim komunikatem.
4. Production: po deploy, powtórz kroki 1-3 na `https://habit-coach-ai.onrender.com/`.
5. Production: sprawdź Supabase Tables, czy `accounts_user` ma wpis.

## Uwagi dotyczące wydajności

Wszystkie endpointy są server-rendered HTML, jeden zapytanie do DB per request (User lookup przez session). Tailwind CDN to ~50KB pojedynczy hit (cache'owany przez przeglądarkę). NFR PRD (<200ms feedback dla habit logging) nie dotyczy S-01 — auth endpoints nie mają twardych budżetów latencyjnych. Pierwsze zalogowanie po cold-start (jeśli Render Starter, którego używamy, kiedyś zacznie spinać down na free — ale nie, Starter to always-on) byłoby wolniejsze; obecnie nie problem.

## Uwagi dotyczące migracji

Phase 1 wymaga `rm db.sqlite3` lokalnie. Production Supabase jest fresh (deploy nigdy nie skończył sukcesem), więc tam migracja `accounts.0001_initial` + Django built-ins (admin, auth=accounts, contenttypes, sessions) zastosują się czysto. Brak istniejących danych do migracji. **Jeśli kiedykolwiek deploy zakończył się sukcesem PRZED tym planem** (i Supabase ma już built-in `auth_user` table), Phase 4 push może paść z błędem migracji — w takim przypadku: nuke Supabase tables via Supabase dashboard, re-deploy. (Mało prawdopodobne; deploy aktualnie pada na DATABASE_URL.)

## Referencje

- Powiązane wycinki: `@context/foundation/roadmap.md` (S-01)
- Twarde reguły: `@CLAUDE.md` (per-user isolation), `@AGENTS.md` (Hard rules)
- PRD: `@context/foundation/prd.md` (US-01, FR-001, FR-002, AC dla US-01)
- Tech stack: `@context/foundation/tech-stack.md` (Django, uv, has_auth=true)
- Deploy: `@context/foundation/infrastructure.md` (Render setup), `@context/deployment/deploy-plan.md` (Phase 1-7 status)
- Django docs: built-in auth views — `https://docs.djangoproject.com/en/6.0/topics/auth/default/`, custom User model — `https://docs.djangoproject.com/en/6.0/topics/auth/customizing/#substituting-a-custom-user-model`

## Progress

> Konwencja: `- [ ]` oczekujące, `- [x]` wykonane. Dodaj ` — <commit sha>`, gdy krok zostanie zrealizowany. Nie zmieniaj nazw tytułów kroków. Zobacz `references/progress-format.md`.

### Faza 1: User model + accounts app + settings hardening

#### Automatyczne

- [x] 1.1 `manage.py check` przechodzi bez warnings — cacec66
- [x] 1.2 `manage.py makemigrations --check accounts` zwraca "No changes detected" po wygenerowaniu migracji — cacec66
- [x] 1.3 `manage.py migrate` przechodzi — cacec66
- [x] 1.4 Tabela `accounts_user` istnieje w db.sqlite3 — cacec66

#### Ręczne

- [x] 1.5 `manage.py createsuperuser` prosi o email i tworzy konto — cacec66
- [x] 1.6 `manage.py runserver` startuje bez błędu — cacec66
- [x] 1.7 `/admin/` — login po emailu działa, kolumna email widoczna — cacec66

### Faza 2: Auth views + URL wiring

#### Automatyczne

- [x] 2.1 `manage.py check` przechodzi — f582f9e
- [x] 2.2 URL resolver pasuje endpointy: `/`, `/register/`, `/accounts/login/`, `/accounts/logout/` — f582f9e

#### Ręczne

- [x] 2.3 `/register/` zwraca HTML (nawet jeśli nieostylowany) — f582f9e
- [x] 2.4 `/accounts/login/` zwraca HTML — f582f9e
- [x] 2.5 `/` niezalogowany → redirect do `/accounts/login/?next=/` — f582f9e
- [x] 2.6 `/` zalogowany jako superuser → HTML dashboard (template OK lub TemplateDoesNotExist w Phase 3) — f582f9e

### Faza 3: Templates + Tailwind + Dashboard placeholder

#### Automatyczne

- [x] 3.1 `manage.py check` przechodzi bez „template does not exist" dla `registration/login.html` — ec8b381
- [x] 3.2 `manage.py collectstatic --no-input --dry-run` przechodzi — ec8b381

#### Ręczne

- [x] 3.3 `/accounts/login/` — login form z Tailwind styling, polskie etykiety — ec8b381
- [x] 3.4 `/register/` — register form z Tailwind styling, polskie etykiety — ec8b381
- [x] 3.5 Zły email format w register → polski komunikat błędu — ec8b381
- [x] 3.6 Rejestracja happy path: submit → auto-login → redirect do `/` → dashboard z empty-state CTA — ec8b381
- [x] 3.7 `/accounts/logout/` (direct URL) działa, redirect do login — ec8b381
- [x] 3.8 Re-login z istniejącym kontem działa — ec8b381

### Faza 4: Tests + production deploy weryfikacja

#### Automatyczne

- [x] 4.1 `manage.py test accounts` — wszystkie 6 testów zielone — d3419ba
- [x] 4.2 `manage.py check --deploy` — brak critical warnings — d3419ba
- [x] 4.3 Render deploy log pokazuje `Applying accounts.0001_initial... OK` + `gunicorn` start + status `live` — d3419ba

#### Ręczne

- [x] 4.4 `https://habit-coach-ai.onrender.com/accounts/login/` — Tailwind + polski OK — d3419ba
- [x] 4.5 Production: utworzenie nowego konta → auto-login → dashboard — d3419ba
- [x] 4.6 Production: logout via direct URL → redirect do login — d3419ba
- [x] 4.7 Production: re-login → dashboard — d3419ba
- [x] 4.8 Supabase Tables → `accounts_user` istnieje z wpisem — d3419ba
- [x] 4.9 Render Logs — brak 5xx po smoke test scenariuszu — d3419ba
