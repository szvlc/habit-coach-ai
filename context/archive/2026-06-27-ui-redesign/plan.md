# Polished SaaS UI redesign — plan (retrospektywny)

## Przegląd

Post-MVP redesign wizualny aplikacji (kierunek „Dopracowany SaaS"). Dokument spisany
retrospektywnie — praca była wykonana ad-hoc, a ten plik domyka ją jako formalną zmianę
przed archiwizacją. Bez zmian w modelu, migracjach ani logice biznesowej; wyłącznie warstwa
prezentacji (szablony) + jeden test regresyjny.

## Zakres

- **`base.html`** — czcionka Inter, favicon (inline SVG), sticky header z logo + stopka,
  pasek akcentu, gradient tła, komponenty jako **czysty CSS** (`.card`, `.btn-*`, `.form-*`,
  `.empty-state`, `.link`) niezależne od Tailwind Play CDN.
- **Pozostałe 12 szablonów** — dashboard, rekomendacja, toggle, historia, formularze,
  login/rejestracja, reset hasła — przeniesione na klasy komponentów + ikony.
- Zachowane wszystkie stringi wymagane przez testy oraz autoescape rekomendacji.

## Czego NIE robimy

- Zmian w modelach / migracjach / logice biznesowej.
- Zmiany frameworka CSS (zostaje Tailwind CDN + HTMX).

## Faza 1: Redesign + fix regresji

### Kryteria sukcesu

- `uv run python manage.py test` — zielone (73, w tym nowy guard HTMX).
- Wszystkie stringi asercji testów zachowane; autoescape rekomendacji nietknięty.
- Rekomendacja AI odświeża się przez HTMX; proaktywna auto-rekomendacja odpala.

## Progress

### Faza 1: Redesign + fix regresji

- [x] 1.1 Redesign 13 szablonów (Inter, header/stopka, favicon, komponenty CSS, ikony) — 2910944
- [x] 1.2 Fix: przywrócenie biblioteki HTMX + test regresyjny `test_dashboard_loads_htmx_library` — 96a31ec
- [x] 1.3 Pełny zestaw testów zielony (73) — 96a31ec
- [x] 1.4 Wdrożone i zweryfikowane na produkcji (rekomendacja odświeża się) — 96a31ec
