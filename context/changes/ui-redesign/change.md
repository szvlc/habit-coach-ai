---
change_id: ui-redesign
title: Polished SaaS UI redesign
status: implemented
created: 2026-06-27
updated: 2026-06-28
archived_at: null
---

## Notes

Post-MVP redesign wizualny (kierunek „Dopracowany SaaS"), zrobiony ad-hoc i udokumentowany
retrospektywnie. Zakres: Inter, sticky header z logo + stopka, favicon (inline SVG), pasek
akcentu, gradient tła, komponenty na **czystym CSS** (`.card`/`.btn-*`/`.form-*`/`.empty-state`),
ikony, dopracowane stany puste — wszystkie 13 szablonów. Bez zmian w modelu/migracjach.

Regresja wykryta po wdrożeniu: redesign zgubił `<script>` HTMX z `base.html` (atrybuty `hx-*`
zostały), przez co rekomendacja AI przestała się odświeżać, a proaktywna auto-rekomendacja
nie odpalała. Naprawione + dodany test regresyjny `test_dashboard_loads_htmx_library`.

Powiązane commity:
- `2910944` — redesign (13 szablonów)
- `96a31ec` — fix: przywrócenie HTMX + test regresyjny

Nie na roadmapie (polish post-MVP). 73 testy zielone; wdrożone i zweryfikowane na produkcji.
