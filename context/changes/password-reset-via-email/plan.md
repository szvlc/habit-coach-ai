# Password reset via email — plan implementacji

## Przegląd

Piąty wycinek (S-05 `password-reset-via-email`). Dostarcza FR-003: niezalogowany użytkownik z istniejącym kontem klika „Zapomniałem hasła", podaje email, dostaje link, ustawia nowe hasło i loguje się. Budujemy na **wbudowanych widokach Django** (`PasswordResetView`/`PasswordResetConfirmView` + tokeny), które są już wpięte przez `django.contrib.auth.urls`. Dokładamy: konfigurację wysyłki email (SMTP provider-agnostyczny, console w dev / SMTP na prod), 4 szablony stron + plain-text email, oraz link „Zapomniałem hasła" na loginie.

Provider: **Resend** (SMTP), nadawca `onboarding@resend.dev` (tryb testowy — bez weryfikacji domeny). Link ważny 3 dni (Django default). Brak nowego modelu i migracji.

## Analiza stanu obecnego

Z bezpośredniej inspekcji bazy kodu:

- `habit_coach_ai/urls.py:11` — `path("accounts/", include("django.contrib.auth.urls"))` **już wpięte**. To dostarcza trasy i widoki: `password_reset/` (name `password_reset`), `password_reset/done/` (`password_reset_done`), `reset/<uidb64>/<token>/` (`password_reset_confirm`), `reset/done/` (`password_reset_complete`). Widoki istnieją; brakuje tylko szablonów.
- `accounts/models.py` — custom `User` z `USERNAME_FIELD='email'`. Django `PasswordResetForm` wyszukuje konta po polu `email` → kompatybilne bez zmian.
- `habit_coach_ai/settings.py` — **brak jakiejkolwiek konfiguracji email** (`EMAIL_BACKEND` itp.). Sekrety czytane z `os.environ` (wzorzec: `DATABASE_URL` branch — SQLite lokalnie / Postgres na prod).
- `templates/registration/login.html` — ma na dole link „Nie masz konta? Zarejestruj się"; **brak linku resetu hasła**. Styl: Tailwind, `bg-white rounded-lg shadow-sm p-8`, manual render pól, polskie etykiety.
- `templates/registration/` zawiera `login.html`, `register.html` — to katalog, gdzie Django szuka `password_reset_*.html`.
- Brak `EMAIL_*` env w `render.yaml` (deploy-plan) — do dodania w Render env.
- Lekcje (`lessons.md`): success-criteria sign-off czyta output (`check --deploy` = W005+W021); integracja zewnętrznego serwisu wymaga prod-smoke z realnym wywołaniem (ta sama klasa co reset-email — realny SMTP testujemy na prod).

## Pożądany stan końcowy

Po wdrożeniu Phase 1-2:

- Na `/accounts/login/` jest link „Zapomniałem hasła" → `/accounts/password_reset/`.
- `/accounts/password_reset/` (GET): formularz email (Tailwind, spójny z login). (POST): wysyła email z linkiem resetu i redirectuje na `password_reset/done/` — **zawsze**, niezależnie czy email istnieje (brak enumeration).
- Email (plain text, polski) zawiera jednorazowy link `reset/<uidb64>/<token>/`.
- Klik linku → `password_reset_confirm` formularz nowego hasła (z walidatorami Django); po zapisie → `reset/done/` z linkiem do logowania.
- Nowe hasło działa przy logowaniu; stary link/token jednorazowy nie działa ponownie; link wygasa po 3 dniach.
- Lokalnie (console backend) cały flow działa — email + link widoczne w terminalu, bez realnego SMTP.
- Na prod (Render + Resend SMTP env) realny email dociera; reset end-to-end działa.
- ~6 testów flow (locmem backend) zielonych: wysyłka, token-link, ustawienie hasła, login nowym hasłem, brak enumeration, odrzucenie złego/zużytego tokenu.
- `check --deploy` = dokładnie W005+W021.

### Kluczowe odkrycia

- **Django dostarcza całą logikę**: widoki, generowanie/walidację tokenów (`default_token_generator`), `auth.urls`. Implementacja to szablony + config + link — zero nowego modelu/migracji/widoku.
- **SMTP backend jest provider-agnostyczny**: `EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend"` + `EMAIL_HOST/PORT/HOST_USER/HOST_PASSWORD/USE_TLS` z env. Resend: host `smtp.resend.com`, port `587` (TLS), user `resend`, password = Resend API key. Zmiana providera = zmiana env, nie kodu.
- **Dev/prod branch po `EMAIL_HOST`**: brak `EMAIL_HOST` w env → `console.EmailBackend` (email drukowany w terminalu, link klikalny lokalnie bez SMTP); ustawiony → SMTP. Wzorzec jak `DATABASE_URL`.
- **Resend tryb testowy**: `onboarding@resend.dev` jako `DEFAULT_FROM_EMAIL` wysyła bez weryfikacji domeny, ale tylko na adres właściciela konta Resend. Prod smoke musi użyć tego adresu. Podmiana na własną domenę (SPF/DKIM) to późniejszy krok.
- **Brak enumeration**: `PasswordResetView` zawsze redirectuje na done, nawet dla nieistniejącego emaila (Django default) — nie ujawnia, czy konto istnieje. Testowane wprost.
- **Custom User OK**: `PasswordResetForm` filtruje po `email` (aktywni użytkownicy) — działa z `USERNAME_FIELD='email'`.

## Czego NIE robimy

- **Własny model tokenu / własny widok resetu** — używamy wbudowanych Django.
- **Weryfikacja własnej domeny / SPF/DKIM** — tryb testowy Resend (`onboarding@resend.dev`) dla MVP; własna domena później.
- **HTML email / branding** — plain text (lepsza deliverability, prostsze).
- **SDK providera / django-anymail** — wbudowany SMTP backend, zero nowych zależności.
- **Rate-limiting / throttling formularza resetu** — poza MVP (Django nie ma wbudowanego; rozważyć po PMF).
- **Zmiana hasła zalogowanego usera** (`PasswordChangeView`) — to inny flow (FR poza S-05); nie tutaj.
- **Niestandardowy czas wygaśnięcia** — Django default 3 dni (`PASSWORD_RESET_TIMEOUT`).
- **Powiadomienie email o udanej zmianie hasła** — poza zakresem MVP.

## Podejście do implementacji

Dwie fazy. Phase 1 dostarcza całą funkcję lokalnie (config + 6 szablonów + link) — weryfikowalną przez console backend bez realnego SMTP. Phase 2 dodaje testy flow (locmem) i wdrożenie z realnym Resend SMTP + prod smoke. Sekwencja: Phase 2 zależy od Phase 1.

Phase 2 `check --deploy` MUSI zwracać dokładnie W005+W021 (lekcja retro). Prod smoke wymaga `EMAIL_*` w Render env (blok z roadmapy — provider wybrany: Resend).

## Krytyczne szczegóły implementacji

- **Kolejność dev/prod branch**: `EMAIL_BACKEND` musi być ustawiony PRZED użyciem; branch po `os.environ.get("EMAIL_HOST", "")`. Bez `EMAIL_HOST` → console backend, więc lokalny `runserver`/testy ręczne działają bez creds.
- **Resend test mode ogranicza adresatów**: w trybie `onboarding@resend.dev` Resend dostarcza tylko na email właściciela konta. Prod smoke (4.x) musi użyć adresu konta Resend, inaczej email nie dotrze mimo „sukcesu" po stronie aplikacji.
- **Token jednorazowy**: po ustawieniu nowego hasła `default_token_generator` inwaliduje token (hash zależy od hasła) — ponowne użycie linku daje stronę „link nieprawidłowy". Testowane.

## Faza 1: Email config + szablony resetu + link na loginie

### Przegląd

Skonfiguruj wysyłkę email (dev/prod branch), dodaj 6 szablonów (4 strony + email body + subject) i link „Zapomniałem hasła" w login.html. Po tej fazie pełny flow resetu działa lokalnie przez console backend.

### Wymagane zmiany

#### 1. Konfiguracja email w settings

**Plik**: `habit_coach_ai/settings.py`

**Cel**: Wysyłka email provider-agnostyczna; console w dev, SMTP na prod. Klucze z env (puste defaulty, by lokalny `check`/testy działały bez creds).

**Kontrakt**: dodać blok: `EMAIL_HOST = os.environ.get("EMAIL_HOST", "")`; jeśli `EMAIL_HOST` niepuste → `EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"`, `EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))`, `EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")`, `EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")`, `EMAIL_USE_TLS = True`; w przeciwnym razie `EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"`. Zawsze: `DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "onboarding@resend.dev")`. `PASSWORD_RESET_TIMEOUT` — pozostaw default (nie ustawiać).

#### 2. Link „Zapomniałem hasła" na loginie

**Plik**: `templates/registration/login.html`

**Cel**: Wejście do flow resetu z ekranu logowania.

**Kontrakt**: dodać link `<a href="{% url 'password_reset' %}">Zapomniałem hasła</a>` (Tailwind spójny z istniejącym linkiem rejestracji; np. pod polem hasła lub przy linku „Zarejestruj się"). Bez innych zmian.

#### 3. Szablon: formularz prośby o reset

**Plik**: `templates/registration/password_reset_form.html` (nowy)

**Cel**: Strona z polem email. Tailwind spójny z `login.html`. Polski.

**Kontrakt**: extends `base.html`, content z `<form method="post">` + `{% csrf_token %}`, manual render `form.email` (label „Email", błędy), submit „Wyślij link resetujący". Link „Wróć do logowania" → `{% url 'login' %}`.

#### 4. Szablon: prośba wysłana

**Plik**: `templates/registration/password_reset_done.html` (nowy)

**Cel**: Potwierdzenie „jeśli konto istnieje, wysłaliśmy link" (sformułowanie bez ujawniania istnienia konta).

**Kontrakt**: extends `base.html`, komunikat: „Jeśli istnieje konto z tym adresem, wysłaliśmy link do resetu hasła. Sprawdź skrzynkę (i spam)." + link do logowania.

#### 5. Szablon: ustawienie nowego hasła

**Plik**: `templates/registration/password_reset_confirm.html` (nowy)

**Cel**: Formularz nowego hasła (gdy token ważny) lub komunikat o nieprawidłowym/wygasłym linku.

**Kontrakt**: extends `base.html`. `{% if validlink %}` → `<form method="post">` + csrf + manual render `form.new_password1`/`new_password2` (etykiety polskie, błędy walidatorów), submit „Ustaw nowe hasło". `{% else %}` → komunikat „Link nieprawidłowy lub wygasł" + link do ponownego resetu (`{% url 'password_reset' %}`).

#### 6. Szablon: reset zakończony

**Plik**: `templates/registration/password_reset_complete.html` (nowy)

**Cel**: Potwierdzenie zmiany + zachęta do logowania.

**Kontrakt**: extends `base.html`, komunikat „Hasło zostało zmienione." + link „Zaloguj się" → `{% url 'login' %}`.

#### 7. Szablon: treść emaila + temat

**Pliki**: `templates/registration/password_reset_email.html` (nowy), `templates/registration/password_reset_subject.txt` (nowy)

**Cel**: Plain-text email z linkiem resetu (polski) + zwięzły temat.

**Kontrakt**: `password_reset_email.html` — plain text z kontekstem Django (`protocol`, `domain`, `uid`, `token`): zbudować absolutny link `{{ protocol }}://{{ domain }}{% url 'password_reset_confirm' uidb64=uid token=token %}`, krótka polska treść + informacja o ważności linku. `password_reset_subject.txt` — jedna linia, np. „Reset hasła — HabitCoach AI" (bez znaku nowej linii poza końcem).

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py check` przechodzi bez warnings (bez `EMAIL_HOST` w env → console backend)
- `uv run python manage.py check` nie zgłasza „template does not exist" dla tras resetu
- `uv run python manage.py collectstatic --no-input --dry-run` przechodzi
- URL resolver pasuje `password_reset`, `password_reset_done`, `password_reset_confirm`, `password_reset_complete`

#### Weryfikacja ręczna

- `/accounts/login/` — link „Zapomniałem hasła" widoczny, prowadzi do `/accounts/password_reset/`
- `/accounts/password_reset/` — formularz email (Tailwind, polski), submit istniejącego emaila → redirect na done; email + link wydrukowany w terminalu (console backend)
- Klik linku z terminala → formularz nowego hasła; ustawienie → strona „hasło zmienione"; login nowym hasłem działa
- Submit NIEistniejącego emaila → ta sama strona done (brak ujawnienia), brak emaila w terminalu
- Ponowne użycie linku po zmianie hasła → „link nieprawidłowy"

**Uwaga implementacyjna**: Po manualnej weryfikacji pełnego flow lokalnie (console backend), zatrzymaj się przed Phase 2.

---

## Faza 2: Testy (locmem) + deployment verify

### Przegląd

Napisz testy flow w `accounts/tests.py` (locmem email backend), re-verify `check --deploy`, ustaw `EMAIL_*` w Render env (Resend), prod smoke z realnym resetem.

### Wymagane zmiany

#### 1. Testy flow resetu

**Plik**: `accounts/tests.py`

**Cel**: Pokryć FR-003 end-to-end bez realnego SMTP. Klasa z `@override_settings(SECURE_SSL_REDIRECT=False, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")`.

**Kontrakt**: `PasswordResetFlowTests(TestCase)`:
- `test_reset_request_sends_email_with_link` — POST istniejący email na `password_reset` → redirect na done; `mail.outbox` ma 1 wiadomość; treść zawiera link `reset/<uidb64>/<token>/`.
- `test_full_reset_flow_sets_new_password_and_logs_in` — wyciągnij uid/token z outbox, przejdź confirm (GET → redirect na set-password, POST `new_password1`/`new_password2`), następnie login nowym hasłem działa; stare hasło nie.
- `test_reset_unknown_email_does_not_reveal_and_sends_nothing` — POST nieistniejącego emaila → redirect na done; `mail.outbox` puste.
- `test_used_token_link_is_invalid_second_time` — po udanej zmianie ten sam token/link → strona bez `validlink` (nie pozwala ustawić ponownie).
- `test_invalid_token_shows_invalid_link` — sfałszowany token → `validlink=False`.
- (opcjonalnie) `test_login_page_has_reset_link` — `password_reset` URL obecny na stronie logowania.

#### 2. Commit + push + Render env + prod smoke

**Cel**: Wdrożyć z realnym Resend SMTP. Brak migracji.

**Kontrakt**: commit + push; ustawić w Render env: `EMAIL_HOST=smtp.resend.com`, `EMAIL_PORT=587`, `EMAIL_HOST_USER=resend`, `EMAIL_HOST_PASSWORD=<Resend API key>`, `DEFAULT_FROM_EMAIL=onboarding@resend.dev`. (Dodać też do `render.yaml` `envVars` z `sync:false` dla sekretu, jeśli utrzymywany jako IaC.) Prod smoke: reset na adres właściciela konta Resend (ograniczenie trybu testowego).

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py test accounts` — wszystkie zielone (poprzednie + ~6 nowych)
- `uv run python manage.py test` (całość) — green
- `uv run python manage.py check --deploy` (DEBUG=False) — dokładnie 2 warningi (W005, W021)
- Render deploy: service `live` (brak migracji do zastosowania)

#### Weryfikacja ręczna

- Render env ma `EMAIL_HOST=smtp.resend.com` + creds; deploy live
- Production: `/accounts/password_reset/` → podaj adres konta Resend → realny email dociera (sprawdź skrzynkę)
- Production: klik link → ustaw nowe hasło → login nowym hasłem działa
- Resend dashboard → Activity pokazuje wysłany email (status delivered)
- Render Logs — brak 5xx; brak wycieku `EMAIL_HOST_PASSWORD` w logach

**Uwaga implementacyjna**: Po zielonym prod resecie, S-05 gotowy do `/10x-impl-review password-reset-via-email` przed `/10x-archive`.

---

## Strategia testowania

### Testy jednostkowe

- ~6 testów w `accounts/tests.py` (locmem backend, `mail.outbox`): wysyłka+link, pełny flow (request→token→nowe hasło→login), brak enumeration, token jednorazowy, zły token. Klasa z `@override_settings(SECURE_SSL_REDIRECT=False, EMAIL_BACKEND=locmem)`.
- Stała `STRONG_PASSWORD` jak w istniejących testach; nowe hasło inne, by potwierdzić zmianę.

### Testy integracyjne

- Pełny flow HTTP pokryty kombinacją (`self.client` przez wszystkie 4 widoki + `mail.outbox`).
- Production smoke (manual, realny Resend SMTP) potwierdza deliverability end-to-end.

### Kroki testowania ręcznego

1. Lokalnie (console backend): login → „Zapomniałem hasła" → email → done; skopiuj link z terminala → nowe hasło → „hasło zmienione" → login nowym hasłem.
2. Lokalnie: nieistniejący email → done bez emaila w terminalu.
3. Lokalnie: ponów stary link → „link nieprawidłowy".
4. Production: reset na adres konta Resend → realny email → link → nowe hasło → login.

## Uwagi dotyczące wydajności

Wysyłka email jest synchroniczna w request `PasswordResetView` (SMTP do Resend, zwykle <1-2s). Akceptowalne dla MVP (rzadka operacja). Brak N+1, brak nowych zapytań poza Django auth. Brak budżetu NFR dla resetu.

## Uwagi dotyczące migracji

Brak migracji — żaden model nie zmieniony. Zmiana czysto konfiguracyjna + szablony. Forward-only, brak ryzyka danych.

## Referencje

- Powiązane wycinki: `context/foundation/roadmap.md` (S-05)
- Twarde reguły: PRD FR-003; lekcje `context/foundation/lessons.md` (success-criteria; prod-smoke realnym wywołaniem dla integracji zewn. serwisu)
- Wzorzec per-app: `accounts/` + `templates/registration/login.html`
- Django: `PasswordResetView`/`PasswordResetConfirmView`, `django.contrib.auth.urls`, `EMAIL_BACKEND` — `https://docs.djangoproject.com/en/6.0/topics/auth/default/#module-django.contrib.auth.views`
- Resend SMTP: host `smtp.resend.com`, user `resend`, password = API key

## Progress

> Konwencja: `- [ ]` oczekujące, `- [x]` wykonane. Dodaj ` — <commit sha>`, gdy krok zostanie zrealizowany. Nie zmieniaj nazw tytułów kroków. Zobacz `references/progress-format.md`.

### Faza 1: Email config + szablony resetu + link na loginie

#### Automatyczne

- [x] 1.1 `manage.py check` przechodzi bez warnings (bez EMAIL_HOST → console backend) — 9a5f874
- [x] 1.2 `manage.py check` bez „template does not exist" dla tras resetu — 9a5f874
- [x] 1.3 `collectstatic --no-input --dry-run` przechodzi — 9a5f874
- [x] 1.4 URL resolver pasuje password_reset / _done / _confirm / _complete — 9a5f874

#### Ręczne

- [x] 1.5 Link „Zapomniałem hasła" na loginie → `/accounts/password_reset/` — 9a5f874
- [x] 1.6 Formularz email → submit istniejącego → done; email+link w terminalu (console) — 9a5f874
- [x] 1.7 Klik link → nowe hasło → „hasło zmienione" → login nowym hasłem działa — 9a5f874
- [x] 1.8 Nieistniejący email → done bez ujawnienia, brak emaila w terminalu — 9a5f874
- [x] 1.9 Ponowny stary link po zmianie → „link nieprawidłowy" — 9a5f874

### Faza 2: Testy (locmem) + deployment verify

#### Automatyczne

- [x] 2.1 `manage.py test accounts` — zielone (16: 10 + 6 nowych)
- [x] 2.2 `manage.py test` (całość) — green (57)
- [x] 2.3 `manage.py check --deploy` (DEBUG=False) — dokładnie 2 warningi (W005, W021)
- [ ] 2.4 Render deploy: service `live`

#### Ręczne

- [ ] 2.5 Render env: `EMAIL_HOST=smtp.resend.com` + creds; deploy live
- [ ] 2.6 Production: reset na adres konta Resend → realny email dociera
- [ ] 2.7 Production: klik link → nowe hasło → login nowym hasłem działa
- [ ] 2.8 Resend Activity: email delivered; Render Logs brak 5xx / brak wycieku hasła SMTP
