# Password reset via email — plan brief

> Pełny plan: `context/changes/password-reset-via-email/plan.md`

## Co i dlaczego

Piąty slice (S-05). Dostarcza FR-003: niezalogowany użytkownik resetuje zapomniane hasło przez link wysłany na email — domyka braki w pełnej obsłudze konta (rejestracja/login już są; bez resetu zapomniane hasło = utrata konta).

## Punkt wyjścia

Po S-01 istnieje custom `User` (login emailem) i `django.contrib.auth.urls` jest już wpięte — czyli **widoki i trasy resetu Django już działają**, brakuje tylko szablonów, konfiguracji wysyłki email i linku na loginie. Projekt nie ma dziś żadnej konfiguracji email.

## Pożądany stan końcowy

Na ekranie logowania jest „Zapomniałem hasła" → formularz email → email z linkiem → strona nowego hasła → „hasło zmienione" → login nowym hasłem. Lokalnie email+link widać w terminalu (console backend); na prod realny email leci przez Resend SMTP. Brak ujawniania, czy konto istnieje.

## Kluczowe podjęte decyzje

| Decyzja | Wybór | Dlaczego | Źródło |
|---|---|---|---|
| Silnik resetu | Wbudowane widoki Django | auth.urls już wpięte; tokeny/walidacja gotowe; zero modelu/migracji | Plan |
| Email provider | Resend (SMTP) | Rekomendacja roadmapy; 3000/mc free, prosty setup, dobra deliverability | Roadmap |
| Integracja | Wbudowany SMTP backend Django | Provider-agnostyczny; zero nowych zależności; zmiana providera = zmiana env | Plan |
| Dev vs prod | Console w dev / SMTP na prod (branch po EMAIL_HOST) | Lokalny test bez creds (link w terminalu); wzorzec jak DATABASE_URL | Plan |
| Nadawca | `onboarding@resend.dev` (tryb testowy) | Zero DNS; odblokowuje FR-003 natychmiast; własna domena później | Plan |
| Format emaila | Plain text | Najlepsza deliverability, najprostszy | Plan |
| Ważność linku | Django default (3 dni) | Rozsądny balans; zero konfiguracji | Plan |
| Testy | Pełny flow (locmem backend) | e2e bez realnego SMTP; łapie regresje szablonów/URL/config | Plan |

## Zakres

**W zakresie:** email-config (dev/prod branch, env creds), 4 szablony stron resetu + plain-text email + subject, link „Zapomniałem hasła" na loginie, testy flow (locmem), deploy z Resend env + prod smoke.

**Poza zakresem:** własny model/widok tokenu; weryfikacja domeny/SPF-DKIM; HTML email; SDK providera/anymail; rate-limiting; zmiana hasła zalogowanego usera; niestandardowy TTL tokenu; email-powiadomienie o zmianie.

## Architektura / Podejście

Django `PasswordResetView`→`password_reset_done`→email z tokenem→`PasswordResetConfirmView`→`password_reset_complete`. My dodajemy: settings email-branch (`EMAIL_HOST` → SMTP, inaczej console; `DEFAULT_FROM_EMAIL` z env), 6 szablonów w `templates/registration/`, link na loginie. Custom User (USERNAME_FIELD=email) kompatybilny z `PasswordResetForm`. SMTP provider-agnostyczny — Resend creds w Render env.

## Fazy w skrócie

| Faza | Co dostarcza | Kluczowe ryzyko |
|---|---|---|
| 1. Config + szablony + link | Pełny flow działa lokalnie (console backend) | Poprawny branch dev/prod; szablony w registration/ |
| 2. Testy + deploy | Testy flow (locmem) + Resend SMTP na prod + smoke | Deliverability (spam); tryb testowy Resend wysyła tylko do właściciela konta |

**Wymagania wstępne:** S-01 (zarejestrowani użytkownicy) ✓; konto Resend + API key w Render env (przed prod smoke).
**Szacowany nakład pracy:** ~2 sesje w 2 fazach (Django robi większość; bulk to szablony + config).

## Otwarte ryzyka i założenia

- Deliverability: tryb testowy Resend (`onboarding@resend.dev`) dostarcza tylko na adres właściciela konta — prod smoke musi użyć tego adresu; pełna wysyłka wymaga własnej zweryfikowanej domeny (później).
- SMTP synchroniczny w request (~1-2s) — akceptowalne dla rzadkiej operacji resetu w MVP.

## Kryteria sukcesu (podsumowanie)

- Użytkownik z zapomnianym hasłem odzyskuje dostęp: email → link → nowe hasło → login.
- Brak ujawniania istnienia konta (zawsze „jeśli konto istnieje…"); token jednorazowy, wygasa po 3 dniach.
- Realny email dociera na prod (Resend); pełny flow przetestowany (locmem) + smoke.
