# Logout — plan implementacji

## Przegląd

Siódmy i ostatni wycinek MVP (S-07 `logout`). Dostarcza FR-004 (nice-to-have): zalogowany użytkownik klika „Wyloguj", sesja jest unieważniona, ląduje na ekranie logowania. Cała logika (URL, view, redirect) już istnieje out-of-the-box — brakuje tylko kontrolki w UI. Domyka roadmapę MVP.

## Analiza stanu obecnego

Z bezpośredniej inspekcji bazy kodu:

- `habit_coach_ai/urls.py` — `django.contrib.auth.urls` wpięte (S-01) → trasa `logout/` (name `logout`) + Django `LogoutView` istnieją. **Django 6.0 `LogoutView` przyjmuje wyłącznie POST** (GET usunięty w Django 5.0).
- `habit_coach_ai/settings.py:148` — `LOGOUT_REDIRECT_URL = 'login'` **już ustawione** → po wylogowaniu redirect na `/accounts/login/`.
- `templates/base.html:13-17` — header zawiera tylko link-logo (`<a href="dashboard">HabitCoach AI</a>`). **Brak kontrolki wylogowania.** Header renderuje się na każdej stronie (i dla zalogowanych, i nie).
- `base.html` ma `hx-headers` z CSRF na `<body>`, ale formularz logout użyje własnego `{% csrf_token %}` (zwykły POST form, nie HTMX).
- Brak modelu/migracji w grze. Zero nowych tras (logout/ istnieje). Zero zmian settings.
- Wzorce: Tailwind, polskie etykiety, testy z `@override_settings(SECURE_SSL_REDIRECT=False)` + stała `STRONG_PASSWORD`.

## Pożądany stan końcowy

Po wdrożeniu Fazy 1:

- Header (`base.html`) dla **zalogowanego** użytkownika pokazuje po prawej email + przycisk „Wyloguj" (formularz POST); logo zostaje po lewej.
- Dla **niezalogowanego** (login/rejestracja/reset) header nie pokazuje kontrolki wylogowania (`{% if user.is_authenticated %}`).
- Klik „Wyloguj" → POST `/accounts/logout/` → sesja unieważniona → redirect na `/accounts/login/`.
- GET `/accounts/logout/` → 405 (POST-only) — nie da się wylogować przez nawigację/prefetch.
- ~3-4 testy zielone (POST wylogowuje + redirect, GET 405, widoczność kontrolki authed/anon).
- `check --deploy` = W005+W021. Prod smoke: zaloguj → Wyloguj → login.

### Kluczowe odkrycia

- **POST-only**: Django 6 `LogoutView` odrzuca GET (405). Kontrolka MUSI być `<form method="post" action="{% url 'logout' %}">{% csrf_token %}<button>…</button></form>`, nie `<a href>`. To też zabezpiecza przed wylogowaniem przez `<img>`/prefetch/CSRF.
- **Reuse istniejącej infrastruktury**: `logout/` URL + `LogoutView` + `LOGOUT_REDIRECT_URL='login'` już są. Zmiana to wyłącznie szablon + testy.
- **Header globalny**: edycja `base.html` daje wylogowanie z każdej strony; `{% if user.is_authenticated %}` chowa kontrolkę na stronach auth.

## Czego NIE robimy

- **Strona potwierdzenia wylogowania** — bezpośredni jeden klik (PRD: „klika → sesja unieważniona → ekran logowania").
- **Komunikat „zostałeś wylogowany"** — redirect na login wystarcza; brak dodatkowego baneru (można dodać przez Django messages później).
- **Zmiany `LogoutView` / własny widok** — wbudowany Django.
- **Wylogowanie ze wszystkich urządzeń / sesji** — pojedyncza sesja (MVP single-device per PRD).
- **Zmiany w settings / modelu / migracji** — brak.

## Podejście do implementacji

Jedna faza: edycja headera `base.html` (flex: logo + email + „Wyloguj" POST gdy authenticated) + testy (POST/GET-405/widoczność) + deploy z prod smoke. Reuse Django `LogoutView`.

Faza 1 `check --deploy` = dokładnie W005+W021 (lekcja retro).

## Faza 1: Kontrolka wylogowania w headerze + testy + deploy

### Przegląd

Dodaj kontrolkę „Wyloguj" (POST) + email zalogowanego w headerze `base.html`, napisz testy, zweryfikuj deploy + prod smoke. Domyka MVP.

### Wymagane zmiany

#### 1. Header z kontrolką wylogowania

**Plik**: `templates/base.html`

**Cel**: Zalogowany user może się wylogować z każdej strony; kontrolka ukryta dla niezalogowanych.

**Kontrakt**: przebuduj `<header>` na układ poziomy (Tailwind `flex items-center justify-between`): po lewej istniejący link-logo do `accounts:dashboard`; po prawej — `{% if user.is_authenticated %}` blok z małym tekstem `{{ user.email }}` + `<form method="post" action="{% url 'logout' %}">{% csrf_token %}<button type="submit">Wyloguj</button></form>` (Tailwind spójny, przycisk dyskretny). Brak innych zmian w base.

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py check` przechodzi
- `uv run python manage.py collectstatic --no-input --dry-run` przechodzi
- `uv run python manage.py test accounts` — zielone (poprzednie + ~3-4 nowe logout)
- `uv run python manage.py test` (całość) — green
- `uv run python manage.py check --deploy` (DEBUG=False) — dokładnie 2 warningi (W005, W021)

#### Weryfikacja ręczna

- Zalogowany na `/` → header pokazuje email + „Wyloguj"
- Klik „Wyloguj" → redirect na `/accounts/login/`; powrót na `/` → przekierowanie do logowania (sesja unieważniona)
- Niezalogowany na `/accounts/login/` → brak kontrolki „Wyloguj" w headerze
- Production: zaloguj → „Wyloguj" → login; brak 5xx

**Uwaga implementacyjna**: Po automatycznej weryfikacji + manualnym/prod smoke, S-07 gotowy do `/10x-impl-review logout` (opcjonalnie) i `/10x-archive` — domyka MVP.

### Testy

**Plik**: `accounts/tests.py`

**Cel**: Pokryć FR-004 + bezpieczeństwo (GET nie wylogowuje) + widoczność kontrolki.

**Kontrakt**: `LogoutTests(TestCase)` z `@override_settings(SECURE_SSL_REDIRECT=False)`:
- `test_logout_post_invalidates_session_and_redirects` — zaloguj, POST `logout`, sprawdź redirect na `login` + brak `_auth_user_id` w sesji.
- `test_logout_get_not_allowed` — GET `logout` → 405 (Django 6 POST-only).
- `test_header_shows_logout_when_authenticated` — GET `/` zalogowany → odpowiedź zawiera `action="…/logout/"` (lub „Wyloguj").
- `test_header_hides_logout_when_anonymous` — GET `/accounts/login/` (anon) → brak kontrolki logout.

---

## Strategia testowania

### Testy jednostkowe

- ~4 testy w `accounts/tests.py`: POST wylogowuje + redirect, GET 405, widoczność authed/anon. Klasa z `@override_settings(SECURE_SSL_REDIRECT=False)`.

### Kroki testowania ręcznego

1. Lokalnie: zaloguj → header z emailem + „Wyloguj" → klik → login; spróbuj wejść na `/` → redirect do logowania.
2. Lokalnie: na stronie logowania brak kontrolki „Wyloguj".
3. Production: zaloguj na onrender.com → „Wyloguj" → login.

## Uwagi dotyczące wydajności

Brak. Logout to jedno żądanie POST obsługiwane przez Django; header bez dodatkowych zapytań (user już w request).

## Uwagi dotyczące migracji

Brak migracji — zmiana wyłącznie szablonu + testy.

## Referencje

- Powiązane wycinki: `context/foundation/roadmap.md` (S-07); per-app wzorzec `accounts/` (S-01)
- PRD FR-004 (nice-to-have); lekcje `context/foundation/lessons.md` (success-criteria output)
- Django: `LogoutView` (POST-only od 5.0), `django.contrib.auth.urls`, `LOGOUT_REDIRECT_URL`

## Progress

> Konwencja: `- [ ]` oczekujące, `- [x]` wykonane. Dodaj ` — <commit sha>`, gdy krok zostanie zrealizowany. Nie zmieniaj nazw tytułów kroków. Zobacz `references/progress-format.md`.

### Faza 1: Kontrolka wylogowania w headerze + testy + deploy

#### Automatyczne

- [x] 1.1 `manage.py check` przechodzi
- [x] 1.2 `collectstatic --no-input --dry-run` przechodzi
- [x] 1.3 `manage.py test accounts` — zielone (poprzednie + 4 nowe `LogoutTests`)
- [x] 1.4 `manage.py test` (całość) — green (72 testy OK)
- [x] 1.5 `manage.py check --deploy` (DEBUG=False) — dokładnie 2 warningi (W005, W021)

#### Ręczne

- [ ] 1.6 Zalogowany: header z emailem + „Wyloguj"; klik → login; sesja unieważniona
- [ ] 1.7 Niezalogowany (login): brak kontrolki „Wyloguj" w headerze
- [ ] 1.8 GET `/accounts/logout/` → 405 (POST-only)
- [ ] 1.9 Production: zaloguj → „Wyloguj" → login; brak 5xx
