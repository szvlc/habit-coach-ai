# Habit analytics — plan implementacji

## Przegląd

Post-MVP funkcja: osobna strona `/habits/analytics/` z wizualizacją postępów użytkownika za ostatnie
30 dni. Dwie warstwy: (1) **karty metryk per-nawyk** (aktualny streak, % ukończenia, najsłabszy dzień,
liczba wykonań) oraz (2) **agregatowy słupkowy wykres 30 dni** — ile aktywnych nawyków zostało zrobionych
każdego dnia. **Renderowane w całości serwerowo (Tailwind CSS + inline SVG), zero nowego JS/CDN** — decyzja
poparta badaniami (`research.md`) i lekcjami F1/F5. Zero zmian w modelu/migracji.

## Analiza stanu obecnego

Z `research.md` (bezpośrednia inspekcja):

- Warstwa danych gotowa: `build_history_context(user)` (`habits/recommendations.py:35`) zwraca per-nawyk
  `{name, done_count, current_streak, completion_rate, weakest_weekday, last_break}` + `days` (30 dat).
- Surowy zbiór `done` = `HabitExecution.objects.history_for(user, start).values_list("habit_id","date")`
  pozwala policzyć dzienną agregację (ile nawyków zrobionych danego dnia).
- Istniejący wzorzec widoku: `HabitHistoryView(LoginRequiredMixin, TemplateView)` (`habits/views.py:89`).
- `HISTORY_DAYS=30` zduplikowane (`habits/views.py:22` + `habits/recommendations.py:18`) — do scentralizowania.
- Konwencje testów: `@override_settings(SECURE_SSL_REDIRECT=False)`, `STRONG_PASSWORD`, izolacja per-user,
  `*_requires_login`.
- Izolacja per-user: każdy queryset filtruje `request.user` — twardy guardrail.

## Pożądany stan końcowy

- Trasa `habits:analytics` (`/habits/analytics/`), tylko dla zalogowanych; anon → redirect na login.
- Strona pokazuje **wyłącznie dane request.user**: karty per-nawyk + słupkowy wykres dzienny 30 dni.
- Słupek dnia: wysokość ∝ (liczba nawyków zrobionych tego dnia / liczba aktywnych nawyków); dziś wyróżniony.
- Pusty stan, gdy brak aktywnych nawyków (spójny z resztą UI: `.empty-state`).
- Link „Analityka" na dashboardzie obok „Historia".
- `HISTORY_DAYS` scentralizowane (import z `recommendations`), duplikat w `views.py` usunięty.
- ~6 testów zielonych (izolacja, login, metryki, agregat dzienny, link, pusty stan). Całość zielona.
- `check --deploy` = dokładnie W005+W021 (bez regresji).

### Kluczowe odkrycia

- **Zero nowej biblioteki**: dane małe (30 dni × kilka nawyków), istniejący grid już jest heatmapą CSS,
  a lekcje F1/F5 odradzają niepinowane CDN w stronach logowanych. SVG/CSS serwerowo wygrywa.
- **Reużycie `build_history_context`**: karty dostają gotowe sygnały; dzienny agregat liczony z `done`.
- **Brak HTMX na tej stronie**: statyczny render (żadnych `hx-*`), więc żadnego nowego długu JS.

## Czego NIE robimy

- Żadnej biblioteki wykresów (Chart.js/d3/cal-heatmap) ani nowego skryptu CDN.
- Żadnych zmian w modelu, migracji, ani w logice AI/rekomendacji.
- Żadnej interaktywności JS (zoom, tooltipy JS) — tytuły natywne (`title=`) wystarczą w v1.
- Żadnego eksportu/filtrów zakresu dat — tylko okno 30 dni (spójne z historią).

## Podejście do implementacji

Jedna faza: funkcja `build_daily_completion(user)` (czysta, testowalna) + `HabitAnalyticsView` + trasa +
szablon `analytics.html` (karty + słupki SVG/CSS) + link na dashboardzie + centralizacja `HISTORY_DAYS`
+ testy. Reużycie `build_history_context`.

## Faza 1: Widok analityki + wizualizacja serwerowa + testy

### Wymagane zmiany

#### 1. Agregacja dzienna (czysta funkcja)

**Plik**: `habits/recommendations.py`

**Kontrakt**: dodaj `build_daily_completion(user)` zwracającą listę 30 elementów
`[{date, done_count, total, ratio}]`, gdzie `total` = liczba aktywnych nawyków usera, `done_count` = ile z
nich miało wykonanie danego dnia, `ratio` = `done_count/total` (0 gdy `total==0`). Liczone z tego samego
`done` set co `build_history_context` (reużyj `HISTORY_DAYS`, `history_for`). Wyłącznie dane `user`.

#### 2. Widok analityki

**Plik**: `habits/views.py`

**Kontrakt**: `HabitAnalyticsView(LoginRequiredMixin, TemplateView)`, `template_name="habits/analytics.html"`.
`get_context_data` woła `build_history_context(request.user)` (→ `habits` karty, `today`) i
`build_daily_completion(request.user)` (→ `daily`). Usuń duplikat `HISTORY_DAYS` z `views.py` — importuj
z `habits.recommendations`.

#### 3. Trasa

**Plik**: `habits/urls.py`

**Kontrakt**: `path("analytics/", views.HabitAnalyticsView.as_view(), name="analytics")`.

#### 4. Szablon

**Plik**: `templates/habits/analytics.html`

**Kontrakt**: extends `base.html`, `{% block container_width %}max-w-2xl{% endblock %}`. Nagłówek + link
powrotny „Dashboard" (wzorzec z `history.html`). Sekcja słupkowa: 30 słupków (inline SVG lub div-bary
Tailwind, wysokość ∝ `ratio`), słupek `today` wyróżniony (indigo), `title` z datą i `done_count/total`.
Karty per-nawyk: `.card`/grid z nazwą, streak, `completion_rate`%, `weakest_weekday`, `done_count`/30.
Pusty stan `.empty-state`, gdy brak nawyków. Zero `<script>`.

#### 5. Link nawigacyjny

**Plik**: `templates/accounts/dashboard.html`

**Kontrakt**: obok linku „Historia" dodaj link „Analityka" → `{% url 'habits:analytics' %}` (spójny styl `.link`).

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py check` przechodzi
- `uv run python manage.py test habits accounts` — zielone (poprzednie + ~6 nowe)
- `uv run python manage.py test` (całość) — green
- `uv run python manage.py check --deploy` (DEBUG=False) — dokładnie W005+W021

#### Weryfikacja ręczna

- Zalogowany z danymi → `/habits/analytics/` pokazuje karty + słupki 30 dni; dziś wyróżniony
- Niezalogowany → redirect na login
- Użytkownik bez nawyków → pusty stan
- Dashboard → link „Analityka" prowadzi na stronę

### Testy

**Plik**: `habits/tests.py`

**Kontrakt**: `HabitAnalyticsViewTests(TestCase)` z `@override_settings(SECURE_SSL_REDIRECT=False)`:
- `test_analytics_requires_login` — anon GET → 302 na login.
- `test_analytics_shows_only_own_habits` — nawyk innego usera nieobecny w `context["habits"]`/odpowiedzi.
- `test_analytics_metrics_reflect_executions` — po zalogowaniu N wykonań: `completion_rate`/`done_count`/streak zgodne.
- `test_analytics_empty_state_when_no_habits` — brak nawyków → pusty stan (`assertContains` komunikat).
- `test_daily_completion_counts_per_day_only_own` — jednostkowy `build_daily_completion`: poprawny `done_count`/`total`/długość 30, ignoruje cudze i zarchiwizowane.
- `test_dashboard_has_analytics_link` — dashboard zawiera `href` do `habits:analytics`.

## Strategia testowania

- ~6 testów w `habits/tests.py` (widok + czysta funkcja agregacji). Izolacja per-user jak w istniejących
  testach; brak sieci/LLM (funkcja czysto lokalna).

## Kroki testowania ręcznego

1. Zaloguj, oznacz kilka wykonań, wejdź `/habits/analytics/` → karty + słupki, dziś wyróżniony.
2. Wyloguj → `/habits/analytics/` przekierowuje na login.
3. Konto bez nawyków → pusty stan.
4. Dashboard → „Analityka" → strona.

## Uwagi dotyczące wydajności

Brak. Jedno zapytanie `history_for` (jak istniejąca historia) + agregacja w Pythonie na ≤30×N elementach.

## Uwagi dotyczące migracji

Brak — zmiana wyłącznie prezentacji + jedna czysta funkcja. Zero zmian modelu.

## Referencje

- `context/changes/habit-analytics/research.md` (M2L4 — badania wewn.+zewn.)
- Wzorce: `HabitHistoryView` (`habits/views.py:89`), `build_history_context` (`habits/recommendations.py:35`)
- Lekcje: F1/F5 (`context/foundation/lessons.md`) — zero nowego CDN/JS
- PRD guardrail: izolacja per-user

## Progress

> Konwencja: `- [ ]` oczekujące, `- [x]` wykonane. Dodaj ` — <commit sha>` przy realizacji kroku.

### Faza 1: Widok analityki + wizualizacja serwerowa + testy

#### Automatyczne

- [ ] 1.1 `build_daily_completion` + `HabitAnalyticsView` + trasa + szablon + link + centralizacja HISTORY_DAYS
- [ ] 1.2 `manage.py check` przechodzi
- [ ] 1.3 `manage.py test habits accounts` — zielone (+~6 nowych)
- [ ] 1.4 `manage.py test` (całość) — green
- [ ] 1.5 `manage.py check --deploy` (DEBUG=False) — dokładnie W005+W021

#### Ręczne

- [ ] 1.6 Zalogowany z danymi: karty + słupki 30 dni, dziś wyróżniony
- [ ] 1.7 Niezalogowany: redirect na login
- [ ] 1.8 Bez nawyków: pusty stan
- [ ] 1.9 Dashboard: link „Analityka" działa
