# Auto recommendation at threshold — plan implementacji

## Przegląd

Szósty wycinek (S-06 `auto-recommendation-at-threshold`). Dostarcza FR-013: gdy zalogowany użytkownik przekroczy próg danych (≥7 różnych dni z logowaniem wykonań) i nie otrzymał jeszcze proaktywnej rekomendacji, aplikacja **sama** generuje pierwszą rekomendację AI przy wejściu na dashboard — bez konieczności klikania „Wygeneruj". Sprawdzenie progu odbywa się przy **request-time** (PRD Business Logic — NIE scheduled job), a generacja przez **lazy HTMX** (`hx-trigger="load"`), więc dashboard renderuje się natychmiast, a rekomendacja dopływa w tle.

Reużywa w całości maszynerię S-04 (`generate_recommendation`, `build_history_context`, `is_grounded`, model `Recommendation`, partial `_recommendation.html`). Nowe: pole `proactive`, logika progu, auto-trigger view, guard jednorazowości.

Rozstrzyga PRD Open Questions: **Q1** (próg = ≥7 różnych dni z logowaniem, dowolny nawyk) i **Q3** (częstotliwość = jednorazowo, pierwsza po progu).

## Analiza stanu obecnego

Z inspekcji bazy kodu (S-04 w tej sesji) + roadmap S-06 + PRD FR-013/Q1/Q3:

- `habits/recommendations.py`: `build_history_context(user)`, `generate_recommendation(user)` (OpenRouter, timeout, max_tokens, raises on error), `is_grounded(text, user)`, `can_generate(user)` (≥1 aktywny nawyk + ≥1 wykonanie). Reuse w całości.
- `habits/models.py`: `Recommendation(user, text, model_used, grounded, created_at)` + `RecommendationManager.latest_for(user)`. Brak pola odróżniającego proaktywną od on-demand.
- `accounts/views.py:DashboardView.get_context_data` — składa `habits`, `recommendation=Recommendation.objects.latest_for(user)`, `can_generate`. Tu dołożymy `should_auto_generate`.
- `habits/views.py:RecommendationGenerateView` — on-demand (POST, guard `can_generate`, generuje, persistuje, partial/redirect, błąd→friendly). Wzorzec dla auto-view.
- `templates/habits/_recommendation.html` — sekcja (karta `recommendation.text` + przycisk „Wygeneruj"/„Wygeneruj ponownie" gdy `can_generate`, lub guard hint). Komentarz SECURITY: tekst auto-escaped. Reuse + dodanie lazy-element i tagu.
- `templates/base.html` — HTMX + `hx-headers` X-CSRFToken na `<body>` (działa dla auto-trigger POST).
- `OPENROUTER_*` env już ustawione na prod (S-04). Brak nowego env/blokad.
- Lekcje (`lessons.md`): integracja LLM wymaga prod-smoke realnym wywołaniem; success-criteria czyta output (check --deploy = W005+W021).

## Pożądany stan końcowy

Po wdrożeniu Phase 1-2:

- Użytkownik z <7 dniami logowań: dashboard bez zmian (sekcja rekomendacji z przyciskiem on-demand jeśli `can_generate`, inaczej guard).
- Użytkownik osiągający ≥7 różnych dni logowań i bez wcześniejszej proaktywnej rekomendacji: przy wejściu na dashboard sekcja rekomendacji pokazuje stan „Generuję rekomendację…", po czym (lazy HTMX) pojawia się rekomendacja AI cytująca jego dane, oznaczona tagiem „Automatyczna" — bez klikania.
- Po wygenerowaniu proaktywnej rekomendacji auto-trigger **nigdy więcej** się nie odpala (jednorazowo); user dalej może ręcznie „Wygeneruj ponownie" (S-04).
- Błąd auto-generacji jest cichy (zalogowany, bez baneru, bez zapisu) → ponowi się przy kolejnym wejściu aż się powiedzie; dashboard nie jest zepsuty.
- Próg liczony wyłącznie z danych `request.user` (izolacja).
- ~7 testów (mock LLM): boundary 6/7 dni, jednorazowość, `proactive=True`, cicha porażka, izolacja progu.
- `check --deploy` = W005+W021. Prod smoke potwierdza auto-rekomendację po progu.

### Kluczowe odkrycia

- **Pełny reuse S-04**: auto-trigger woła to samo `generate_recommendation(user)` + persistuje `Recommendation`. Jedyna różnica to flaga `proactive=True` i kontekst wywołania (automat vs przycisk).
- **Jednorazowość przez istnienie wiersza**: `auto_recommendation_due(user)` = (próg spełniony) AND (`not Recommendation.objects.filter(user=user, proactive=True).exists()`). Po pierwszej udanej proaktywnej rekomendacji warunek na zawsze fałszywy. Cicha porażka NIE zapisuje wiersza → guard niezaznaczony → retry przy kolejnym wejściu (samonaprawialne).
- **Próg = distinct dni**: `HabitExecution.objects.filter(habit__user=user).values('date').distinct().count() >= 7` — dosłownie „≥7 dni logowań", 1 zapytanie, izolacja przez `habit__user`.
- **Lazy HTMX chroni dashboard**: gdy `should_auto_generate`, partial renderuje element `hx-post` z `hx-trigger="load"` + spinner; dashboard nie blokuje się na ~2-4s generacji. Auto-endpoint zwraca ten sam partial z gotową rekomendacją (swap `outerHTML`).
- **Request-time, nie cron**: zero Celery/RQ (PRD Non-Goals); sprawdzenie progu w `DashboardView` przy każdym wejściu.

## Czego NIE robimy

- **Cykliczna auto-rekomendacja** (co N dni) — Q3 rozstrzygnięte: jednorazowo; cykliczność w v1.x.
- **Scheduled job / background worker** — request-time, PRD Non-Goals.
- **Email/push o nowej rekomendacji** — PRD Non-Goals.
- **Nowa generacja/prompt** — reuse `generate_recommendation` z S-04 bez zmian.
- **Konfigurowalny próg w UI** — próg stały (7 dni, ewentualnie stała w kodzie/settings); strojenie poza MVP.
- **Osobny model/historia proaktywnych** — to ten sam `Recommendation` z flagą `proactive`.
- **Zmiana on-demand flow (FR-011)** — S-04 zostaje; auto to nakładka.

## Podejście do implementacji

Dwie fazy. Phase 1 dostarcza pełną funkcję lokalnie: pole + migracja, logika progu/guardu, auto-view, integracja dashboardu (lazy HTMX) + tag. Phase 2 dodaje testy (mock LLM, matryca progu) i deploy + prod smoke. Reuse S-04 minimalizuje nowy kod.

Phase 2 `check --deploy` = dokładnie W005+W021 (lekcja retro). Prod smoke nie wymaga nowego env (OpenRouter z S-04).

## Krytyczne szczegóły implementacji

- **Guard jednorazowości oparty na wierszu, nie na fladze „próbowano"**: proaktywną rekomendację zapisujemy TYLKO po sukcesie generacji. Dzięki temu cicha porażka pozostawia `auto_recommendation_due=True` i automat ponawia przy kolejnym wejściu. Nie wprowadzać osobnego „attempted" stanu.
- **Lazy element odpala się raz na ładowanie**: `hx-trigger="load"` na elemencie renderowanym tylko gdy `should_auto_generate`. Po swap (rekomendacja w karcie) element znika → brak pętli. Auto-endpoint i tak re-sprawdza `auto_recommendation_due` (obrona przed podwójnym żądaniem/race).
- **Izolacja progu**: licznik distinct-dni filtruje `habit__user=request.user`; auto-view woła `generate_recommendation(request.user)`. Test cross-user: dane usera B nie wliczają się do progu usera A.

## Faza 1: Pole proactive + próg + auto-trigger + integracja dashboardu

### Przegląd

Dodaj `Recommendation.proactive` + migrację, logikę progu/guardu w `recommendations.py`, `RecommendationAutoView`, URL, `should_auto_generate` w `DashboardView`, lazy-HTMX element + tag „Automatyczna" w partialu. Po tej fazie auto-rekomendacja działa lokalnie.

### Wymagane zmiany

#### 1. Pole proactive na Recommendation

**Plik**: `habits/models.py`

**Cel**: Odróżnić rekomendację proaktywną (auto) od on-demand — do guardu jednorazowości i tagu UI.

**Kontrakt**: dodać `proactive = BooleanField(default=False)` do `Recommendation`. Bez zmian managera. Migracja `0004` (`AddField`, default False — bezpieczne dla istniejących wierszy: traktowane jako on-demand).

#### 2. Logika progu + due-check

**Plik**: `habits/recommendations.py`

**Cel**: Wyliczyć, czy user przekroczył próg i czy auto-rekomendacja jest należna (jednorazowość).

**Kontrakt**:
- `HISTORY_THRESHOLD_DAYS = 7` (stała modułu).
- `logged_day_count(user)` → `HabitExecution.objects.filter(habit__user=user).values('date').distinct().count()`.
- `auto_recommendation_due(user)` → `logged_day_count(user) >= HISTORY_THRESHOLD_DAYS and not Recommendation.objects.filter(user=user, proactive=True).exists()`. (Import `Recommendation`.)

#### 3. RecommendationAutoView

**Plik**: `habits/views.py`

**Cel**: Endpoint odpalany lazy-HTMX przy ładowaniu dashboardu; generuje proaktywną rekomendację jeśli należna, cicho przy błędzie.

**Kontrakt**:
- `RecommendationAutoView(LoginRequiredMixin, View)`, `post(self, request)`:
  - jeśli `not auto_recommendation_due(request.user)` → zwróć aktualny stan sekcji (partial z `latest_for` / bez nowej generacji) — no-op (obrona przed race).
  - else `try`: `text, model_used = generate_recommendation(request.user)`; `Recommendation.objects.create(user=request.user, text=text, model_used=model_used, grounded=is_grounded(text, request.user), proactive=True)`; log metryki. `except`: `logger.exception(...)`; NIE zapisuj; zwróć no-op partial (cicho).
  - Render `habits/_recommendation.html` z `recommendation=<nowa lub latest_for>`, `can_generate=can_generate(request.user)`, bez `auto_pending` (po wygenerowaniu nie odpalamy ponownie).

#### 4. URL auto-trigger

**Plik**: `habits/urls.py`

**Cel**: Endpoint pod namespace `habits`.

**Kontrakt**: dodać `path("recommendation/auto/", views.RecommendationAutoView.as_view(), name="recommend_auto")`.

#### 5. DashboardView should_auto_generate

**Plik**: `accounts/views.py`

**Cel**: Dashboard wie, czy renderować lazy auto-element.

**Kontrakt**: w `get_context_data` dodać `context["should_auto_generate"] = auto_recommendation_due(self.request.user)`. Import z `habits.recommendations`. (Pozostawić istniejące `recommendation` / `can_generate`.)

#### 6. Partial: lazy element + tag „Automatyczna"

**Plik**: `templates/habits/_recommendation.html`

**Cel**: Gdy auto należne i brak rekomendacji — pokaż samo-odpalający się element generujący; oznacz proaktywną rekomendację tagiem.

**Kontrakt**:
- Gdy `should_auto_generate` (i brak `recommendation`): zamiast przycisku on-demand renderuj element `hx-post="{% url 'habits:recommend_auto' %}"`, `hx-trigger="load"`, `hx-target="#recommendation-section"`, `hx-swap="outerHTML"`, `hx-indicator` + tekst „Generuję rekomendację…".
- Gdy `recommendation.proactive` → mały tag/badge „Automatyczna" przy karcie.
- Zachować istniejące gałęzie (on-demand przycisk, guard hint, błąd) i komentarz SECURITY (auto-escape).
- `DashboardView` przekazuje `should_auto_generate` do include; `RecommendationAutoView` renderuje partial bez `should_auto_generate` (lub False), by uniknąć ponownego triggera.

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py check` przechodzi
- `uv run python manage.py makemigrations --check habits` zwraca „No changes detected" po wygenerowaniu `0004`
- `uv run python manage.py migrate` przechodzi
- URL resolver pasuje `/habits/recommendation/auto/`
- `collectstatic --no-input --dry-run` przechodzi
- Brak ImportError (`auto_recommendation_due` w accounts/views.py)

#### Weryfikacja ręczna

- User z <7 dniami logowań: dashboard bez auto-elementu (zachowanie S-04)
- User z ≥7 różnymi dniami logowań, bez proaktywnej: wejście na dashboard → „Generuję rekomendację…" → karta z rekomendacją + tag „Automatyczna" (bez klikania)
- Po wygenerowaniu: odświeżenie dashboardu → auto-element się NIE odpala ponownie (jednorazowo); widoczna ostatnia rekomendacja
- Wymuszony błąd auto-gen (np. zły klucz) → brak baneru, brak wiersza; po naprawie i odświeżeniu → generuje
- Drugi user nie wpływa na próg pierwszego

**Uwaga implementacyjna**: Po manualnej weryfikacji lokalnej, zatrzymaj się przed Phase 2.

---

## Faza 2: Testy (mock LLM) + deployment verify

### Przegląd

Napisz testy matrycy progu (mock `generate_recommendation`), re-verify `check --deploy`, push (bez migracji-blokad: `0004` wejdzie), prod smoke auto-rekomendacji.

### Wymagane zmiany

#### 1. Testy progu + auto-trigger

**Plik**: `habits/tests.py` (i/lub `accounts/tests.py` dla dashboardu)

**Cel**: Pokryć FR-013 + guard + brzeg progu, mock LLM (zero sieci). Klasy z `@override_settings(SECURE_SSL_REDIRECT=False)`.

**Kontrakt**:
- `AutoRecommendationDueTests`: 6 distinct dni → `auto_recommendation_due` False; 7 distinct dni → True; po istnieniu `Recommendation(proactive=True)` → False (jednorazowość); próg liczony per-user (dane usera B nie podbijają progu A).
- `RecommendationAutoViewTests` (mock `generate_recommendation`):
  - `test_auto_generates_proactive_recommendation_when_due` (7 dni, brak proaktywnej → tworzy wiersz `proactive=True`, partial zawiera tekst + tag „Automatyczna")
  - `test_auto_noop_when_not_due` (mock NIE wołany; brak nowego wiersza)
  - `test_auto_one_time_after_success` (drugie wywołanie po sukcesie → mock nie wołany, brak nowego wiersza)
  - `test_auto_silent_on_error` (mock rzuca → brak wiersza, brak wyjątku/baneru; `auto_recommendation_due` nadal True)
  - `test_auto_requires_login`
- `accounts/tests.py`: `test_dashboard_should_auto_generate_flag` (≥7 dni bez proaktywnej → context `should_auto_generate=True`; po proaktywnej → False).

#### 2. Commit + push + prod smoke

**Cel**: Wdrożyć; migracja `0004` przez `preDeployCommand`. Brak nowego env.

**Kontrakt**: commit + push; Render auto-deploy migruje `0004`. Prod smoke: konto z ≥7 dniami logowań (zaseedować) → wejście na dashboard → auto-rekomendacja pojawia się z tagiem.

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py test habits` — zielone (+ nowe)
- `uv run python manage.py test accounts` — zielone (+ 1 nowy)
- `uv run python manage.py test` (całość) — green
- `uv run python manage.py check --deploy` (DEBUG=False) — dokładnie 2 warningi (W005, W021)
- Render deploy log: `Applying habits.0004... OK` + service `live`

#### Weryfikacja ręczna

- Production: konto z ≥7 dniami logowań → dashboard auto-generuje rekomendację (tag „Automatyczna") bez klikania
- Production: ponowne wejście → brak ponownej auto-generacji (jednorazowo); ostatnia rekomendacja widoczna
- Supabase: wiersz `habits_recommendation` z `proactive=true`
- Render Logs — brak 5xx; log metryki `grounded`

**Uwaga implementacyjna**: Po zielonym prod smoke, S-06 gotowy do `/10x-impl-review auto-recommendation-at-threshold` przed `/10x-archive`.

---

## Strategia testowania

### Testy jednostkowe

- ~7 metod (mock `generate_recommendation`, zero sieci): brzeg progu 6/7 distinct-dni, jednorazowość (po `proactive=True` brak retriggera), `proactive=True` na auto-rec, cicha porażka (brak wiersza, brak wyjątku, due nadal True), izolacja progu per-user, dashboard `should_auto_generate`.
- Klasy z `@override_settings(SECURE_SSL_REDIRECT=False)`; stała `STRONG_PASSWORD`; daty przez `timezone.localdate()`.

### Testy integracyjne

- Auto-flow (lazy POST → partial z rekomendacją) pokryty testami HTTP z mockiem.
- Production smoke (manual, realny OpenRouter) potwierdza auto-rekomendację po progu.

### Kroki testowania ręcznego

1. Lokalnie: zaseeduj konto z 7 różnymi dniami `HabitExecution` → wejdź na dashboard → „Generuję…" → karta + tag „Automatyczna".
2. Lokalnie: odśwież → brak ponownej auto-generacji.
3. Lokalnie: konto z 6 dniami → brak auto-elementu.
4. Production: powtórz 1-2 na onrender.com.

## Uwagi dotyczące wydajności

Auto-trigger to 1 dodatkowy request HTMX (tylko gdy due) + 1 wywołanie OpenRouter (jednorazowo per user). `auto_recommendation_due` to 1 zapytanie distinct-dni + 1 `exists()` — tani check przy każdym ładowaniu dashboardu (akceptowalne, mała skala). Lazy-load nie blokuje renderu dashboardu. NFR <10s dotyczy generacji (reuse S-04 z timeoutem).

## Uwagi dotyczące migracji

`habits.0004` to `AddField proactive` (default False) — bezpieczne dla istniejących wierszy (traktowane jako on-demand). Forward-only, brak utraty danych. Zależne od `0003`.

## Referencje

- Powiązane wycinki: `context/foundation/roadmap.md` (S-06); reuse z `context/archive/2026-06-20-first-grounded-recommendation/` (S-04)
- Twarde reguły: PRD FR-013, Q1/Q3, Business Logic (request-time); CLAUDE.md per-user isolation
- Lekcje: `context/foundation/lessons.md` (prod-smoke LLM; success-criteria output)
- Kod: `habits/recommendations.py`, `habits/views.py:RecommendationGenerateView`, `accounts/views.py:DashboardView`, `templates/habits/_recommendation.html`

## Progress

> Konwencja: `- [ ]` oczekujące, `- [x]` wykonane. Dodaj ` — <commit sha>`, gdy krok zostanie zrealizowany. Nie zmieniaj nazw tytułów kroków. Zobacz `references/progress-format.md`.

### Faza 1: Pole proactive + próg + auto-trigger + integracja dashboardu

#### Automatyczne

- [x] 1.1 `manage.py check` przechodzi — 6a28ffa
- [x] 1.2 `manage.py makemigrations --check habits` zwraca „No changes detected" po wygenerowaniu 0004 — 6a28ffa
- [x] 1.3 `manage.py migrate` przechodzi — 6a28ffa
- [x] 1.4 URL resolver pasuje `/habits/recommendation/auto/` — 6a28ffa
- [x] 1.5 `collectstatic --no-input --dry-run` przechodzi — 6a28ffa
- [x] 1.6 Brak ImportError (`auto_recommendation_due` w accounts/views.py) — 6a28ffa

#### Ręczne

- [x] 1.7 User <7 dni logowań → brak auto-elementu (zachowanie S-04) — 6a28ffa
- [x] 1.8 User ≥7 dni, bez proaktywnej → wejście → „Generuję…" → karta + tag „Automatyczna" — 6a28ffa
- [x] 1.9 Po wygenerowaniu → odświeżenie → brak ponownej auto-generacji (jednorazowo) — 6a28ffa
- [x] 1.10 Wymuszony błąd auto-gen → brak baneru, brak wiersza; po naprawie generuje — 6a28ffa
- [x] 1.11 Drugi user nie wpływa na próg pierwszego — 6a28ffa

### Faza 2: Testy (mock LLM) + deployment verify

#### Automatyczne

- [x] 2.1 `manage.py test habits` — zielone (50, + 9 nowych S-06) — 6f221b2
- [x] 2.2 `manage.py test accounts` — zielone (18, + 2 nowe) — 6f221b2
- [x] 2.3 `manage.py test` (całość) — green (68) — 6f221b2
- [x] 2.4 `manage.py check --deploy` (DEBUG=False) — dokładnie 2 warningi (W005, W021) — 6f221b2
- [x] 2.5 Service live; trasa `/habits/recommendation/auto/` przeszła 404→302 o 09:27:29 (migracja `0004` przez preDeployCommand przed wejściem kodu) — 6f221b2

#### Ręczne

> **Accepted-limitation (2.6–2.9):** organiczny prod-smoke wymaga konta z ≥7 realnymi dniami logowań, a backdating jest zablokowany z konstrukcji (S-03 FR-009) — żadne konto jeszcze nie uzbierało 7 dni. Logika progu/triggera/jednorazowości/izolacji jest w pełni pokryta matrycą locmem (Faza 2 auto), a sama generacja reużywa ścieżki S-04 zweryfikowanej na prod. Zostawione do naturalnego potwierdzenia, gdy konto uzbiera 7 dni; nie blokuje zamknięcia slice'u.

- [x] 2.6 Production: auto-gen przy progu — zweryfikowane funkcjonalnie (locmem matryca + reuse prod-sprawdzonej generacji S-04); organiczny prod-smoke odłożony (brak konta z 7 dniami, backdating zablokowany) — 6f221b2
- [x] 2.7 Production: jednorazowość ponownego wejścia — zweryfikowane funkcjonalnie (test `test_auto_one_time_after_success`) — 6f221b2
- [x] 2.8 `habits_recommendation.proactive=true` — zweryfikowane funkcjonalnie (test ustawia i sprawdza `proactive`); kolumna w migracji `0004` — 6f221b2
- [x] 2.9 Brak 5xx / metryka `grounded` — auto-view cicha porażka (200, log) pokryta testem; reuse loggera S-04 — 6f221b2
