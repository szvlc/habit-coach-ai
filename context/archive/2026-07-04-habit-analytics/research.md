---
date: 2026-07-04T16:05:08+0200
researcher: Claude (10x-research)
git_commit: d1dd17c3f777c8f7c656208dfbddda4c9ea929bb
branch: main
repository: habit-coach-ai
topic: "Dashboard z wizualizacją postępów nawyków (30 dni) — jak zbudować, co reużyć, jaką bibliotekę wybrać"
tags: [research, codebase, habits, analytics, visualization, htmx, charting]
status: complete
last_updated: 2026-07-04
last_updated_by: Claude (10x-research)
---

# Research: wizualizacja postępów nawyków (habit-analytics)

**Date**: 2026-07-04T16:05:08+0200 · **Branch**: main · **Commit**: d1dd17c · **Repo**: habit-coach-ai

## Research Question

Jak zbudować dashboard/sekcję z wizualizacją postępów nawyków (30 dni), co można reużyć z istniejącej
warstwy danych, i **jaką bibliotekę** przyjąć pod stack Django + HTMX + Tailwind (CDN, bez build-stepu)?
Ćwiczenie M2L4: badania wewnętrzne + zewnętrzne → decyzja poparta dowodami.

## Summary

- **Warstwa danych jest w pełni gotowa do reużycia — zero zmian w modelu/migracji.** Cała potrzebna
  agregacja już istnieje w `build_history_context(user)` (`habits/recommendations.py:35`) i w surowym
  zbiorze `done` = `HabitExecution.objects.history_for(user, start).values_list("habit_id","date")`.
- **Istniejący widok historii (`HabitHistoryView`) to już serwerowa heatmapa** w CSS-owej siatce
  (`templates/habits/history.html`) — dowód, że wizualizacja bez JS jest naturalna dla tego stacku.
- **Decyzja o bibliotece (rdzeń M2L4):** badania zewnętrzne wskazują Chart.js jako domyślny wybór
  (CDN, ~60 KB, canvas), ale to **koliduje z naszymi własnymi lekcjami F1/F5** (`context/foundation/lessons.md`):
  niepinowane zależności CDN w stronach uwierzytelnionych = ryzyko supply-chain, a Tailwind Play CDN jest
  „not for production". **Rekomendacja: wizualizacja renderowana serwerowo (Tailwind CSS + inline SVG),
  zero nowego JS, zero nowego CDN.** Tańsze, bezpieczniejsze, izolacja per-user zostaje po stronie serwera.
- Integracja: nowy `HabitAnalyticsView(LoginRequiredMixin, TemplateView)` + trasa `habits:analytics`
  + szablon dziedziczący z `base.html`, LUB sekcja wbudowana w dashboard. Wzorce testów gotowe do skopiowania.

## Detailed Findings

### Warstwa danych (reużywalna w całości)

- `HabitExecutionManager.history_for(user, since)` — `habits/models.py:41` — wykonania usera, tylko aktywne nawyki, `date>=since`. Per-user przez `habit__user=user`.
- `HabitExecutionManager.done_habit_ids_for(user, date)` — `habits/models.py:36` — set PK nawyków zrobionych danego dnia.
- `HabitManager.active(user)` — `habits/models.py:6` — aktywne (nie zarchiwizowane) nawyki usera.
- `build_history_context(user)` — `habits/recommendations.py:35-89` — zwraca `{today, start, days:[30 dat], habits:[{name, done_count, current_streak, completion_rate, weakest_weekday, last_break}]}`. **To gotowy zestaw sygnałów do kart/wykresów.**
- Surowy zbiór do heatmapy: `set((habit_id, date))` z `history_for` — dokładnie to, czego używa istniejąca siatka.

### Istniejąca siatka 30 dni (wzorzec do rozszerzenia)

- `HabitHistoryView.get_context_data` — `habits/views.py:92-111` — buduje `days`, `rows=[{habit, cells:[{date, done}]}]`.
- `templates/habits/history.html:14-45` — renderuje to jako tabelę kwadracików (`bg-green-500` done / `bg-gray-100` nie, `ring-indigo-400` dziś). **To już heatmapa bez JS.**

### Punkty integracji (widok/URL/szablon/nawigacja)

- Widok: dołóż `HabitAnalyticsView(LoginRequiredMixin, TemplateView)` w `habits/views.py` (wzorzec jak `HabitHistoryView`).
- URL: `habits/urls.py` → `path("analytics/", ..., name="analytics")` (app_name `habits`).
- Szablon: `templates/habits/analytics.html` extends `base.html`, `{% block container_width %}max-w-2xl/4xl{% endblock %}`, klasy `.card`.
- Nawigacja: link na dashboardzie (`templates/accounts/dashboard.html:44` obok „Historia").
- CSRF/HTMX globalnie z `base.html:104` (`hx-headers`), gdyby sekcja była HTMX-owa (tu niepotrzebne — statyczny render).

### Konwencje testów (do skopiowania)

- `@override_settings(SECURE_SSL_REDIRECT=False)`, stała `STRONG_PASSWORD` (`habits/tests.py:15`).
- Izolacja: `test_*_rejects_other_users_*_with_404`, `test_*_requires_login`.
- Guard biblioteki: `accounts/tests.py:test_dashboard_loads_htmx_library` (wzorzec `assertContains(response, "<lib>")`).

## Badania zewnętrzne (substytut exa/Context7 → WebSearch)

Porównanie bibliotek wykresów/heatmap 2026:

- **Chart.js** — najpopularniejszy general-purpose, CDN, canvas, ~60 KB (tree-shake do ~14 KB przy bundlu). Domyślny wybór dla vanilla+CDN. ([chartjs.org](https://www.chartjs.org/), [fusioncharts guide](https://www.fusioncharts.com/blog/best-javascript-charting-libraries/))
- **Cal-Heatmap** — heatmapa kalendarzowa, ale **wymaga d3** (ciężka zależność). ([cal-heatmap.com](https://cal-heatmap.com/), [github](https://github.com/wa0x6e/cal-heatmap))
- **Heat.js / g1eb calendar-heatmap** — lekkie, zero-dependency heatmapy SVG. ([jqueryscript list](https://www.jqueryscript.net/blog/best-github-style-calendar-heatmap.html))
- **Chartist** — lekki, SVG + CSS. **Pure SVG/CSS** — brak zależności w ogóle (już używane w istniejącej siatce).

**Wniosek z zestawienia dowodów:** żadna z bibliotek CDN nie bije opcji „render serwerowy + CSS/SVG" dla tego
konkretnego stacku, bo: (1) dane są małe (30 dni × kilka nawyków), (2) już mamy działającą siatkę CSS,
(3) nasze lekcje **F1/F5** świadomie odradzają dokładanie niepinowanych zależności CDN do stron logowanych.

## Architecture Insights

- Wzorzec „manager per-user + TemplateView + context dict" jest spójny w całym repo — nowy widok wpasuje się 1:1.
- Wizualizacja to czysta warstwa prezentacji nad istniejącymi danymi — jak `ui-redesign`, bez dotykania modelu.
- `HISTORY_DAYS=30` jest **zduplikowane** (`habits/views.py:22` i `habits/recommendations.py:18`) — okazja, by scentralizować (import z `recommendations`) przy tej zmianie (por. obserwacja F4 z code review M2L3).

## Historical Context (from prior changes)

- `context/archive/2026-06-27-ui-redesign/` — precedens „warstwa prezentacji, zero modelu", + regresja HTMX (lekcja F5).
- `context/archive/2026-06-13-log-execution-and-history/` — pochodzenie siatki 30 dni.
- `context/foundation/lessons.md` — F1 (CDN pin/SRI), F5 (styling nie usuwa zależności JS), + reguła izolacji per-user.

## Related Research

- Brak wcześniejszych `research.md` (to pierwsze użycie `/10x-research` w projekcie).

## Open Questions

1. **Umiejscowienie:** osobna strona `/habits/analytics/` czy sekcja wbudowana w dashboard? (rekomendacja: osobna strona, spójnie z `/habits/history/`).
2. **Zakres wizualizacji v1:** karty-metryki (streak, %, najsłabszy dzień) + serwerowy słupkowy „ile nawyków zrobionych dziennie przez 30 dni" (CSS bars) — czy też heatmapa per-nawyk (rozszerzenie istniejącej siatki)?
3. **Substytut narzędzi:** exa/Context7 niedostępne — użyto WebSearch; jeśli w przyszłości podłączymy Context7, warto potwierdzić aktualne API wybranej opcji.
