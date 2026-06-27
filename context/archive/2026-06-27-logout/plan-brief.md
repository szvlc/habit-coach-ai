# Logout — brief planu

**Change ID**: `logout` · **Slice**: S-07 (FR-004, nice-to-have) · **Złożoność**: NISKA · **Fazy**: 1

## Co budujemy

Kontrolkę „Wyloguj" w headerze. Zalogowany użytkownik klika → sesja unieważniona → ekran logowania. Domyka MVP (ostatni wycinek).

## Kluczowy wgląd

Cała logika **już istnieje**: trasa `logout/` (z `django.contrib.auth.urls`), Django `LogoutView`, `LOGOUT_REDIRECT_URL='login'`. Brakuje **tylko kontrolki w UI**. Django 6 `LogoutView` jest **POST-only** → formularz POST z CSRF, nie link.

## Zakres

| W zakresie | Poza zakresem |
| --- | --- |
| Header `base.html`: email + „Wyloguj" (POST) gdy `user.is_authenticated` | Strona potwierdzenia wylogowania |
| ~4 testy (POST wylogowuje + redirect, GET→405, widoczność authed/anon) | Komunikat „wylogowano" / baner |
| Deploy + prod smoke | Własny `LogoutView`, zmiany settings/modelu/migracji |

## Jedna faza

**Faza 1 — Kontrolka wylogowania w headerze + testy + deploy**: edytuj `<header>` w `base.html` (flex: logo lewo, email + „Wyloguj" POST prawo, `{% if user.is_authenticated %}`); `LogoutTests` w `accounts/tests.py`; `check --deploy` = W005+W021; prod smoke.

## Gotowość

Po Fazie 1: `/10x-impl-review logout` (opcjonalnie) → `/10x-archive logout` → **MVP domknięty**.
