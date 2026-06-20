# First grounded recommendation — plan implementacji

## Przegląd

Czwarty wycinek (S-04 `first-grounded-recommendation`) — gwiazda przewodnia MVP. Wprowadza rekomendację AI **na żądanie** (FR-011): zalogowany użytkownik klika „Wygeneruj rekomendację", w <10s otrzymuje tekst cytujący jego konkretne nawyki i wzorce z 30-dniowej historii; ostatnia rekomendacja jest widoczna po powrocie do aplikacji (FR-012). Dodaje obserwacyjny token-check (PRD Q2, RESOLVED 2026-06-20) logujący, czy rekomendacja odnosi się do konkretnych danych usera.

Integracja przez **OpenRouter** (OpenAI-compatible) z modelem `anthropic/claude-haiku-4-5` (konfigurowalnym przez env), wywołanie **synchroniczne** z wskaźnikiem HTMX. Twarda reguła domeny (CLAUDE.md): prompt wysyłany do OpenRouter zawiera **wyłącznie dane `request.user`** — per-user isolation jest tu load-bearing przy granicy zewnętrznego API.

**Zakres**: FR-011 (on-demand) + FR-012 (ostatnia widoczna). **NIE** FR-013 (proaktywna po progu) — to S-06.

## Analiza stanu obecnego

Z inspekcji bazy kodu (S-02/S-03 w tej sesji) + roadmap S-04 + PRD + infrastructure.md:

- `habits/` app: `Habit` (+ `HabitManager.active(user)`), `HabitExecution` (+ `HabitExecutionManager.done_habit_ids_for` / `history_for(user, since)` → `filter(habit__user=user, habit__archived=False, date__gte=since)`). To źródło danych do groundingu.
- `accounts/views.py:DashboardView` (`LoginRequiredMixin + TemplateView`) — `get_context_data` już składa `habits` (z done-today). Naturalne miejsce na sekcję rekomendacji + `can_generate`.
- `habit_coach_ai/settings.py`: sekrety z `os.environ` (wzorzec: `SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]`); brak jakiejkolwiek konfiguracji AI. `pyproject.toml` — brak klienta LLM/HTTP.
- `OPENROUTER_API_KEY` to ustalona konwencja env (infrastructure.md §Historia operacyjna „twarde guardraile"; deploy `render.yaml` ma `OPENROUTER_API_KEY` z `sync: false`). Budget alert $20/mo, model NIE gpt-4 (infra risk register).
- NFR: rekomendacja widoczna <10s; jeśli dłużej — widoczny progres/stan pośredni co ≥2s. Haiku realnie ~2-4s → synchronicznie + spinner mieści budżet; klauzula „co 2s" (tylko gdy >10s) praktycznie nie wchodzi przy twardym timeoutie <10s.
- Wzorce: CBV + `LoginRequiredMixin`, manager-on-model, HTMX (`hx-post`/`hx-swap="outerHTML"`, CSRF przez `hx-headers` w `base.html`, partiale), testy z `@override_settings(SECURE_SSL_REDIRECT=False)` + stała `STRONG_PASSWORD`.
- Lekcje (`lessons.md`): success-criteria sign-off czyta output; UniqueConstraint na polach spoza formularza (nie dotyczy tu — brak formularza).

## Pożądany stan końcowy

Po wdrożeniu Phase 1-4:

- Dashboard zalogowanego z ≥1 aktywnym nawykiem i ≥1 wykonaniem pokazuje sekcję rekomendacji z przyciskiem „Wygeneruj rekomendację". Klik → spinner „Generuję…" (HTMX) → w <10s karta z tekstem AI cytującym konkretne nawyki/wzorce usera.
- Bez danych (brak nawyków lub brak wykonań) → zamiast przycisku empty-state z instrukcją („dodaj nawyk i zaloguj wykonanie").
- Ostatnia wygenerowana rekomendacja jest widoczna na dashboardzie po powrocie (FR-012), bez ponownego klikania.
- Błąd/timeout OpenRouter → przyjazny komunikat („Nie udało się wygenerować, spróbuj ponownie"), bez zapisu wiersza, przycisk zostaje.
- Każda generacja zapisuje wiersz `Recommendation(user, text, model_used, grounded, created_at)`; `grounded` = wynik token-checka (czy tekst cytuje ≥1 konkretny token z danych usera). Metryka logowana.
- Prompt do OpenRouter zawiera wyłącznie dane bieżącego usera; cudze dane nigdy nie wyciekają (testowane).
- Django admin pokazuje `Recommendation` z `grounded` i filtrem.
- ~16 testów (mock LLM) zielonych: assembly+sygnały, token-check, guard, izolacja, persystencja-ostatniej, błędy, view. `check --deploy` = W005+W021. Prod smoke z realnym OpenRouter.

### Kluczowe odkrycia

- **Per-user isolation na granicy zewnętrznego API**: builder promptu czerpie WYŁĄCZNIE z `Habit.objects.active(user)` + `HabitExecution.objects.history_for(user, start)`. Nigdy nie iteruje globalnie. To jedyny słuszny punkt egzekwowania — test wprost sprawdza, że prompt usera B nie zawiera nawyków usera A.
- **OpenRouter = OpenAI-compatible**: `openai` SDK z `base_url="https://openrouter.ai/api/v1"` + `api_key=settings.OPENROUTER_API_KEY`. `client.chat.completions.create(model=..., messages=..., timeout=<~9s>)`. Brak `anthropic` SDK.
- **Model przez env**: `OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-haiku-4-5")` — zmiana modelu bez deployu kodu (iteracja w S-06).
- **Token-check obserwacyjny (Q2)**: po generacji `is_grounded(text, user)` sprawdza obecność ≥1 konkretnego tokenu (nazwa aktywnego nawyku, case-insensitive; ewentualnie nazwa najsłabszego dnia tygodnia). Wynik zapisany w `Recommendation.grounded` + zalogowany. **Bez bramki** — rekomendacja zawsze pokazywana, nawet jeśli `grounded=False` (chroni NFR/koszt; iteracja na promptcie).
- **Sygnały groundingu liczone w Pythonie**: dla każdego aktywnego nawyku z okna 30 dni — current streak (kolejne dni do dziś), completion rate (% z 30 dni), najsłabszy dzień tygodnia, ostatnia przerwa. To dokładnie „konkretne elementy", które kryterium 75% nagradza; dają modelowi policzone wzorce zamiast surowej siatki.
- **Latencja**: twardy `timeout` na wywołaniu (~9s) chroni NFR <10s; przekroczenie → wyjątek → przyjazny error (ścieżka błędu, nie wisi).

## Czego NIE robimy

- **FR-013 (proaktywna rekomendacja po progu ~7 dni)** — to S-06. Tu tylko on-demand (FR-011).
- **Historia rekomendacji w UI** (PRD Non-Goals) — wiersze zapisujemy (metryka), ale UI pokazuje tylko ostatnią.
- **Streaming tokenowy / SSE** — synchronicznie + spinner (świadomy tradeoff; Haiku <10s).
- **Background jobs (Celery/RQ)** — PRD Non-Goals; wywołanie request-time.
- **Bramkowanie/regeneracja gdy generyczne** — Q2 rozstrzygnięte: obserwacyjnie, bez retry-on-generic.
- **Auto-retry przy błędzie API** — pojedyncza próba, user klika ponownie (chroni NFR/koszt).
- **Wybór/test wielu modeli, eval harness** — jeden model przez env; iteracja w S-06.
- **Korelacja request-id ↔ OpenRouter usage / middleware telemetrii** (infra wspomina) — poza MVP slice.
- **Markdown/rich rendering odpowiedzi AI** — plain text (escaped); brak renderowania HTML z modelu (bezpieczeństwo).

## Podejście do implementacji

Czterofazowo, z podziałem logika/UI typowym dla integracji AI: Phase 1 stawia dane+config (model, deps, env), Phase 2 buduje czystą logikę (assembly promptu + sygnały + wywołanie LLM + token-check) testowalną bez UI i bez realnego API (mock), Phase 3 dokłada view + sekcję dashboardu (HTMX), Phase 4 domyka testy (mock) + deploy z realnym smoke. Sekwencja topologiczna — Phase 3 zależy od service z Phase 2, Phase 2 od modelu z Phase 1.

Phase 4 `check --deploy` MUSI zwracać dokładnie W005+W021 (lekcja retro). Prod smoke wymaga `OPENROUTER_API_KEY` w Render env (roadmap §Blokady — załatwione w `infrastructure.md` Phase 2 lub do ustawienia przed smoke).

## Krytyczne szczegóły implementacji

- **Klucz API może być pusty lokalnie**: `OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")` (NIE `os.environ[...]` — inaczej `check`/testy lokalne bez klucza wywalą się przy imporcie). Testy mockują wywołanie, więc klucz niepotrzebny lokalnie; prod ma go z Render env.
- **Latencja jako twardy timeout**: wywołanie OpenRouter z `timeout ≈ 9s`. Bez tego powolna generacja przekracza NFR <10s i wisi. Timeout → wyjątek → ścieżka błędu.
- **Izolacja w promptcie (load-bearing)**: builder przyjmuje `user` i czerpie tylko z jego querysetów. Żaden kod assembly nie wykonuje zapytania bez filtra `user`. Test cross-user sprawdza brak cudzych nazw w prompcie.
- **Bezpieczeństwo wyjścia AI**: tekst rekomendacji renderowany przez `{{ }}` (auto-escape) — bez `|safe`/markdown-to-HTML. Model nie wstrzyknie HTML/JS do strony.

## Faza 1: Recommendation model + deps + settings/env + admin + migracja

### Przegląd

Dodaj zależność `openai`, konfigurację OpenRouter w settings (z env), model `Recommendation` + manager, admin, migrację `0003`. Po tej fazie dane i config istnieją; brak logiki/UI.

### Wymagane zmiany

#### 1. Zależność openai

**Plik**: `pyproject.toml` + `uv.lock`

**Cel**: Klient do OpenRouter (OpenAI-compatible). Dojrzałe SDK z timeout/retry/parsowaniem.

**Kontrakt**: `uv add openai`. Pojawia się w `[project.dependencies]` + lock.

#### 2. Konfiguracja OpenRouter w settings

**Plik**: `habit_coach_ai/settings.py`

**Cel**: Wystawić klucz, model i timeout z env (z bezpiecznymi defaultami, by lokalny `check`/testy działały bez klucza).

**Kontrakt**: dodać `OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")`, `OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-haiku-4-5")`, `OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"`, `OPENROUTER_TIMEOUT = float(os.environ.get("OPENROUTER_TIMEOUT", "9"))`. Brak innych zmian.

#### 3. Recommendation model + manager

**Plik**: `habits/models.py`

**Cel**: Persystencja rekomendacji dla FR-012 + metryki Q2 (`grounded`). Manager eksponuje „ostatnia dla usera".

**Kontrakt**:
- `RecommendationManager(models.Manager)`: `latest_for(user)` → `self.filter(user=user).order_by("-created_at").first()`.
- `Recommendation(models.Model)`:
  - `user = ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name="recommendations")`
  - `text = TextField()`
  - `model_used = CharField(max_length=100)` (który model OpenRouter wygenerował)
  - `grounded = BooleanField(default=False)` (wynik token-checka)
  - `created_at = DateTimeField(auto_now_add=True)`
  - `objects = RecommendationManager()`
  - `class Meta`: `ordering = ["-created_at"]`
  - `__str__` → `f"Rec for {self.user} @ {self.created_at:%Y-%m-%d}"`

#### 4. RecommendationAdmin

**Plik**: `habits/admin.py`

**Cel**: Ops/debug + ręczny spot-check metryki Q2 (przegląd próbki + `grounded`).

**Kontrakt**: `@admin.register(Recommendation)` z `list_display = ('user', 'model_used', 'grounded', 'created_at')`, `list_filter = ('grounded', 'model_used', 'created_at')`, `search_fields = ('user__email', 'text')`, `ordering = ('-created_at',)`.

#### 5. Migracja

**Plik**: `habits/migrations/0003_recommendation.py` (wygenerowanie)

**Cel**: Tabela `habits_recommendation`.

**Kontrakt**: `uv run python manage.py makemigrations habits` → `migrate`. `0003` z `CreateModel`, zależna od `0002`. Forward-only, brak destrukcyjnych operacji.

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py check` przechodzi bez warnings (bez `OPENROUTER_API_KEY` w env — default pusty)
- `uv run python manage.py makemigrations --check habits` zwraca „No changes detected" po wygenerowaniu
- `uv run python manage.py migrate` przechodzi
- Tabela `habits_recommendation` istnieje w db.sqlite3
- `uv run python -c "import openai"` (lub przez `uv run python manage.py shell`) — import działa

#### Weryfikacja ręczna

- `/admin/` — sekcja „Recommendations" z list_display + filtrem po `grounded`
- `manage.py shell`: `from django.conf import settings; settings.OPENROUTER_MODEL` zwraca `anthropic/claude-haiku-4-5`

**Uwaga implementacyjna**: Po automatycznej weryfikacji zatrzymaj się na potwierdzenie admina + configu przed Phase 2.

---

## Faza 2: Prompt assembly + sygnały + LLM service + token-check

### Przegląd

Dodaj moduł `habits/recommendations.py` z czystą logiką: zbudowanie kontekstu danych usera (30-dniowa tabela + sygnały), złożenie promptu, wywołanie OpenRouter (sync, timeout, błędy), token-check ugruntowania. Brak UI — wszystko testowalne jednostkowo z mockiem klienta.

### Wymagane zmiany

#### 1. Builder kontekstu + sygnały

**Plik**: `habits/recommendations.py` (nowy)

**Cel**: Złożyć z danych usera (tylko jego) strukturę do promptu: per aktywny nawyk 30-dniowa siatka wykonań + policzone sygnały. Load-bearing isolation.

**Kontrakt**: `build_history_context(user)` → struktura (np. lista dict per nawyk) zawierająca: `name`, siatkę 30 dni (data → done bool), oraz sygnały: `current_streak` (kolejne dni do dziś z wykonaniem), `completion_rate` (% z 30 dni), `weakest_weekday` (dzień tygodnia z najniższym completion), `last_break` (ostatni dzień bez wykonania / długość ostatniej przerwy). Czerpie WYŁĄCZNIE z `Habit.objects.active(user)` + `HabitExecution.objects.history_for(user, today-29d)`. Okno liczone przez `timezone.localdate()`.

#### 2. Złożenie promptu

**Plik**: `habits/recommendations.py`

**Cel**: Zbudować `messages` dla chat-completion z explicit grounding instruction (polski).

**Kontrakt**: `build_messages(context)` → lista `messages` (system + user). System: rola „trener nawyków", instrukcja: odnoś się WYŁĄCZNIE do konkretnych nazw nawyków i wzorców z danych, NIE dawaj generycznych porad („pij wodę", „śpij 8h"). User: sformatowany kontekst (nazwy + sygnały + zwięzła siatka). Polski.

#### 3. Wywołanie OpenRouter (service)

**Plik**: `habits/recommendations.py`

**Cel**: Pojedyncze synchroniczne wywołanie z timeout i propagacją błędu.

**Kontrakt**: `generate_recommendation(user)` → buduje kontekst+messages, tworzy `OpenAI(base_url=settings.OPENROUTER_BASE_URL, api_key=settings.OPENROUTER_API_KEY)`, woła `client.chat.completions.create(model=settings.OPENROUTER_MODEL, messages=..., timeout=settings.OPENROUTER_TIMEOUT)`, zwraca `(text, model_used)`. Wyjątki (timeout, API error) propaguje do wołającego (view łapie). Funkcja jest jednym punktem mockowanym w testach.

#### 4. Token-check ugruntowania

**Plik**: `habits/recommendations.py`

**Cel**: Obserwacyjny pomiar Q2 — czy tekst cytuje konkretne dane usera.

**Kontrakt**: `is_grounded(text, user)` → `bool`. True, gdy `text` (case-insensitive) zawiera ≥1 nazwę aktywnego nawyku usera (ewentualnie też nazwę `weakest_weekday`). Czysta funkcja (nazwy z `Habit.objects.active(user)`). Używana przy zapisie + logowaniu metryki.

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py check` przechodzi
- `uv run python manage.py test habits.tests.<klasy z Phase 2>` — testy logiki zielone (mock klienta): assembly zawiera nazwy+sygnały; sygnały policzone poprawnie na znanych danych; `is_grounded` wykrywa obecność nazwy nawyku i odrzuca generyczny tekst; `generate_recommendation` woła klienta z `settings.OPENROUTER_MODEL` i zwraca tekst (mock); ścieżka błędu propaguje wyjątek
- Brak ImportError

#### Weryfikacja ręczna

- `manage.py shell`: `build_history_context(user)` na seedowanych danych zwraca sensowne sygnały (streak/%/weak-day)
- (Opcjonalnie, jeśli klucz lokalnie dostępny) `generate_recommendation(user)` zwraca tekst cytujący nazwy nawyków

**Uwaga implementacyjna**: Po automatycznej weryfikacji logiki zatrzymaj się przed Phase 3.

---

## Faza 3: View + integracja dashboardu (HTMX)

### Przegląd

Dodaj `RecommendationGenerateView` (POST, guard, persystencja, partial/błąd), URL, sekcję rekomendacji na dashboardzie (przycisk + karta ostatniej + spinner + stany), rozszerz `DashboardView` o ostatnią rekomendację i `can_generate`. Po tej fazie pełny happy path działa lokalnie.

### Wymagane zmiany

#### 1. can_generate helper

**Plik**: `habits/recommendations.py` (lub `models.py`)

**Cel**: Próg danych — ≥1 aktywny nawyk i ≥1 wykonanie.

**Kontrakt**: `can_generate(user)` → `bool`: `Habit.objects.active(user).exists() and HabitExecution.objects.filter(habit__user=user).exists()`.

#### 2. RecommendationGenerateView

**Plik**: `habits/views.py`

**Cel**: Obsłużyć żądanie generowania: guard, wywołanie service, persystencja, partial (HTMX) lub redirect; błąd → komunikat bez zapisu.

**Kontrakt**:
- `RecommendationGenerateView(LoginRequiredMixin, View)`, `post(self, request)`:
  - jeśli `not can_generate(request.user)` → komunikat „dodaj nawyk i zaloguj wykonanie" (partial/redirect), bez wywołania AI.
  - else `try`: `text, model_used = generate_recommendation(request.user)`; `grounded = is_grounded(text, request.user)`; zapisz `Recommendation.objects.create(user=request.user, text=text, model_used=model_used, grounded=grounded)`; zaloguj metrykę (`grounded`). Render partiala karty rekomendacji (HX-Request) albo redirect na dashboard.
  - `except` (błąd/timeout OpenRouter): NIE zapisuj; render partiala/template z komunikatem błędu; zaloguj wyjątek.

#### 3. URL

**Plik**: `habits/urls.py`

**Cel**: Endpoint generowania pod namespace `habits`.

**Kontrakt**: dodać `path("recommendation/generate/", views.RecommendationGenerateView.as_view(), name="recommend")`.

#### 4. Partiale: karta rekomendacji + błąd

**Pliki**: `templates/habits/_recommendation.html` (nowy), ewentualnie `_recommendation_error.html` lub jeden szablon z gałęzią

**Cel**: Render karty z tekstem rekomendacji (auto-escaped) + data; oraz stan błędu z przyciskiem ponów. Reużywany przez view (HTMX swap) i dashboard (ostatnia).

**Kontrakt**: karta extends-free partial: `{{ recommendation.text }}` (escaped, `linebreaks` dozwolone), `{{ recommendation.created_at }}`; przycisk „Wygeneruj ponownie" (hx-post na `habits:recommend`, `hx-target`/`hx-swap` na kontenerze sekcji). Stan błędu: komunikat + przycisk ponów. Spinner przez `hx-indicator`.

#### 5. DashboardView context

**Plik**: `accounts/views.py`

**Cel**: Dashboard zna ostatnią rekomendację i czy można generować.

**Kontrakt**: w `get_context_data` dodać `context["recommendation"] = Recommendation.objects.latest_for(self.request.user)` i `context["can_generate"] = can_generate(self.request.user)`. Import z `habits.models` / `habits.recommendations`.

#### 6. Sekcja rekomendacji na dashboardzie

**Plik**: `templates/accounts/dashboard.html`

**Cel**: Pokazać sekcję rekomendacji: ostatnią (jeśli jest) + przycisk generowania (jeśli `can_generate`) albo empty-state z instrukcją.

**Kontrakt**: kontener sekcji (cel HTMX swap) na górze lub pod listą nawyków: jeśli `recommendation` → include `_recommendation.html`; jeśli `can_generate` i brak rekomendacji → przycisk „Wygeneruj rekomendację" (hx-post, hx-indicator spinner „Generuję…"); jeśli `not can_generate` → hint „Dodaj nawyk i zaloguj wykonanie, by wygenerować rekomendację". Spójny Tailwind.

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py check` przechodzi bez „template does not exist"
- URL resolver pasuje `/habits/recommendation/generate/`
- `collectstatic --no-input --dry-run` przechodzi
- Brak ImportError w accounts/views.py

#### Weryfikacja ręczna

- Dashboard z danymi: przycisk „Wygeneruj rekomendację" + spinner przy kliknięciu; karta z tekstem pojawia się bez reloadu (HTMX)
- Dashboard bez nawyków/wykonań: empty-state z instrukcją (brak przycisku)
- Po odświeżeniu: ostatnia rekomendacja nadal widoczna (FR-012)
- Wymuszony błąd (np. zły klucz/timeout) → komunikat błędu, brak nowego wiersza w DB, przycisk zostaje
- Cudzy dostęp: anon → `/habits/recommendation/generate/` POST → 302 login

**Uwaga implementacyjna**: Po pełnej manualnej weryfikacji lokalnie (z realnym kluczem lub mockiem), zatrzymaj się przed Phase 4.

---

## Faza 4: Testy (mock LLM) + deployment verify

### Przegląd

Napisz testy w `habits/tests.py` (mock wywołania OpenRouter — bez realnego API), dopisz test dashboardu do `accounts/tests.py`, re-verify `check --deploy`, commit + push (Render auto-deploy migracji `0003`), prod smoke z realnym OpenRouter.

### Wymagane zmiany

#### 1. Testy logiki + view (mock LLM)

**Plik**: `habits/tests.py`

**Cel**: Pokryć FR-011/012 + izolację + Q2 token-check + błędy, bez realnych wywołań API. Mock `generate_recommendation` (lub klienta OpenAI) przez `unittest.mock.patch`. Klasy z `@override_settings(SECURE_SSL_REDIRECT=False)`.

**Kontrakt**: Klasy:
- `RecommendationContextTests`: sygnały policzone poprawnie (streak/completion/weak-day/last-break) na znanych danych; kontekst zawiera tylko aktywne nawyki; **cross-user isolation** — kontekst usera B nie zawiera nawyków usera A.
- `IsGroundedTests`: True gdy tekst zawiera nazwę nawyku usera; False dla czysto generycznego tekstu.
- `RecommendationGenerateViewTests` (mock `generate_recommendation`):
  - `test_generate_creates_recommendation_and_shows_text` (mock zwraca tekst → wiersz utworzony, partial zawiera tekst)
  - `test_generated_recommendation_grounded_flag_set` (mock zwraca tekst z nazwą nawyku → `grounded=True`)
  - `test_generate_blocked_without_data` (brak nawyku/wykonania → brak wywołania AI, brak wiersza, komunikat)
  - `test_generate_api_error_shows_message_no_save` (mock rzuca → brak wiersza, komunikat błędu)
  - `test_generate_requires_login`
  - `test_generate_uses_only_request_user_data` (mock przechwytuje `user` przekazany do service — to user z requestu)
- `RecommendationModelTests`: `latest_for` zwraca najnowszą rekomendację usera, nie cudzą.

#### 2. DashboardView recommendation test

**Plik**: `accounts/tests.py`

**Cel**: Dashboard pokazuje ostatnią rekomendację i poprawny `can_generate`.

**Kontrakt**: dodać do `DashboardViewTests`:
- `test_dashboard_shows_latest_recommendation_and_can_generate_flag` — user z nawykiem+wykonaniem+rekomendacją: context ma tę rekomendację jako ostatnią i `can_generate=True`; nie pokazuje cudzej.

#### 3. Commit + push

**Cel**: Push triggeruje Render auto-deploy z migracją `0003`. Prod smoke wymaga `OPENROUTER_API_KEY` w Render env.

**Kontrakt**: commity per faza, push do `origin/main`. Przed prod smoke potwierdź, że `OPENROUTER_API_KEY` jest ustawiony w Render (roadmap §Blokady).

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py test habits` — zielone (~16 nowych + S-02/S-03), zero realnych wywołań sieci (mock)
- `uv run python manage.py test accounts` — zielone (poprzednie + 1 nowy)
- `uv run python manage.py test` — green
- `uv run python manage.py check --deploy` (DEBUG=False) — dokładnie 2 warningi (W005, W021)
- Render deploy log: `Applying habits.0003... OK` + service `live`

#### Weryfikacja ręczna

- Production (z `OPENROUTER_API_KEY` w env): zaloguj, zaloguj wykonanie, „Wygeneruj rekomendację" → tekst <10s cytujący nazwy nawyków
- Production: odśwież → ostatnia rekomendacja widoczna (FR-012)
- Production: konto bez danych → empty-state, brak przycisku
- Supabase Tables → `habits_recommendation` ma wpis z `grounded`
- Render Logs — brak 5xx; log metryki `grounded` widoczny; brak wycieku klucza w logach

**Uwaga implementacyjna**: Po zielonym prod deploy + smoke, S-04 gotowy do `/10x-impl-review first-grounded-recommendation` przed `/10x-archive`.

---

## Strategia testowania

### Testy jednostkowe

- ~16 metod w `habits/tests.py` + 1 w `accounts/tests.py`. Pokrywają FR-011 (generacja+persystencja), FR-012 (ostatnia), Q2 (token-check + `grounded`), próg danych (guard), obsługę błędów, oraz **per-user isolation w prompcie** (kontekst usera nie zawiera cudzych danych).
- **Mock LLM**: `unittest.mock.patch` na `habits.recommendations.generate_recommendation` (dla testów view) i na kliencie OpenAI (dla testu samego service). ZERO realnych wywołań sieciowych w testach.
- Każda klasa z `@override_settings(SECURE_SSL_REDIRECT=False)`; stała `STRONG_PASSWORD`; asercje daty przez `timezone.localdate()`.

### Testy integracyjne

- Pełny flow generuj→pokaż→persystuj pokryty kombinacją testów HTTP (mock service).
- Production smoke (manual, JEDNO realne wywołanie OpenRouter) potwierdza end-to-end z kluczem i migracją `0003` na Supabase.

### Kroki testowania ręcznego

1. Lokalnie (mock lub realny klucz): dashboard z nawykiem+wykonaniem → „Wygeneruj" → spinner → karta z tekstem cytującym nazwę nawyku.
2. Lokalnie: odśwież → ostatnia rekomendacja widoczna.
3. Lokalnie: konto bez danych → empty-state bez przycisku.
4. Lokalnie: wymuś błąd (pusty/zły klucz) → komunikat błędu, brak wiersza w DB.
5. Production: powtórz 1-2 na onrender.com (realny OpenRouter).
6. Production: Supabase `habits_recommendation` ma wpis z `grounded`.

## Uwagi dotyczące wydajności

NFR <10s: wywołanie OpenRouter z twardym `timeout ≈ 9s`; Haiku realnie ~2-4s. Synchroniczny request blokuje jeden gunicorn worker na czas generacji — akceptowalne przy małej skali MVP (infra: Starter, monitoruj CPU). Brak N+1: builder kontekstu czerpie z `history_for` (1 zapytanie executions + 1 habits), sygnały liczone w Pythonie. Dashboard: +1 zapytanie o ostatnią rekomendację (`latest_for`). Klauzula NFR „progres co 2s" wchodzi tylko gdy >10s — twardy timeout sprawia, że nie dochodzi do tego stanu (zamiast tego błąd).

## Uwagi dotyczące migracji

`habits.0003_recommendation` zależy od `0002` (nie dotyka istniejących tabel; nowy model). Forward-only, brak destrukcyjnych operacji. `on_delete=CASCADE` na `user` FK — usunięcie konta usuwa rekomendacje (spójne z owned data). Brak danych do migracji.

## Referencje

- Powiązane wycinki: `context/foundation/roadmap.md` (S-04)
- Twarde reguły: `CLAUDE.md` (per-user isolation, grounding ≥75%), PRD FR-011/012, NFR <10s, Q2 (RESOLVED)
- Infrastruktura: `context/foundation/infrastructure.md` (OpenRouter, `OPENROUTER_API_KEY`, budget $20/mo, model NIE gpt-4)
- Wzorzec per-app: `context/archive/2026-06-13-log-execution-and-history/` (S-03) + `habits/` w bazie kodu
- OpenRouter: OpenAI-compatible, `base_url=https://openrouter.ai/api/v1`; openai SDK `chat.completions.create`
- Lekcje: `context/foundation/lessons.md`

## Progress

> Konwencja: `- [ ]` oczekujące, `- [x]` wykonane. Dodaj ` — <commit sha>`, gdy krok zostanie zrealizowany. Nie zmieniaj nazw tytułów kroków. Zobacz `references/progress-format.md`.

### Faza 1: Recommendation model + deps + settings/env + admin + migracja

#### Automatyczne

- [x] 1.1 `manage.py check` przechodzi bez warnings (bez klucza w env) — 985f63d
- [x] 1.2 `manage.py makemigrations --check habits` zwraca „No changes detected" po wygenerowaniu — 985f63d
- [x] 1.3 `manage.py migrate` przechodzi — 985f63d
- [x] 1.4 Tabela `habits_recommendation` istnieje w db.sqlite3 — 985f63d
- [x] 1.5 `import openai` działa — 985f63d

#### Ręczne

- [x] 1.6 `/admin/` — sekcja „Recommendations" z list_display + filtrem po `grounded` — 985f63d
- [x] 1.7 `settings.OPENROUTER_MODEL` zwraca `anthropic/claude-haiku-4-5` — 985f63d

### Faza 2: Prompt assembly + sygnały + LLM service + token-check

#### Automatyczne

- [x] 2.1 `manage.py check` przechodzi — f92a55b
- [x] 2.2 Testy logiki zielone: sygnały (streak/%/weak-day) policzone poprawnie — f92a55b
- [x] 2.3 Test: `build_history_context` zawiera tylko aktywne nawyki usera (izolacja) — f92a55b
- [x] 2.4 Test: `is_grounded` wykrywa nazwę nawyku, odrzuca generyczny tekst — f92a55b
- [x] 2.5 Test: `generate_recommendation` woła klienta z `OPENROUTER_MODEL` i zwraca tekst (mock); błąd propaguje wyjątek — f92a55b
- [x] 2.6 Brak ImportError — f92a55b

#### Ręczne

- [x] 2.7 `shell`: `build_history_context(user)` na seedowanych danych zwraca sensowne sygnały — f92a55b

### Faza 3: View + integracja dashboardu (HTMX)

#### Automatyczne

- [x] 3.1 `manage.py check` przechodzi bez „template does not exist" — 5ad2ed8
- [x] 3.2 URL resolver pasuje `/habits/recommendation/generate/` — 5ad2ed8
- [x] 3.3 `collectstatic --no-input --dry-run` przechodzi — 5ad2ed8
- [x] 3.4 Brak ImportError w accounts/views.py — 5ad2ed8

#### Ręczne

- [x] 3.5 Dashboard z danymi: przycisk + spinner → karta z tekstem bez reloadu (HTMX) — mechanizm swap zweryfikowany przez test client (partial zwracany, hx-target #recommendation-section); realny tekst w prod smoke 4.6 — 5ad2ed8
- [x] 3.6 Dashboard bez danych: empty-state z instrukcją, brak przycisku — 5ad2ed8
- [x] 3.7 Odświeżenie → ostatnia rekomendacja widoczna (FR-012) — 5ad2ed8
- [x] 3.8 Wymuszony błąd → komunikat, brak nowego wiersza w DB, przycisk zostaje — 5ad2ed8
- [x] 3.9 Anon → `/habits/recommendation/generate/` POST → 302 login — 5ad2ed8

### Faza 4: Testy (mock LLM) + deployment verify

#### Automatyczne

- [x] 4.1 `manage.py test habits` — zielone (40: + 13 nowych S-04), zero realnych wywołań sieci
- [x] 4.2 `manage.py test accounts` — zielone (10: + 1 nowy)
- [x] 4.3 `manage.py test` (całość) — green (50)
- [x] 4.4 `manage.py check --deploy` (DEBUG=False) — dokładnie 2 warningi (W005, W021)
- [ ] 4.5 Render deploy log: `Applying habits.0003... OK` + service `live`

#### Ręczne

- [ ] 4.6 Production: „Wygeneruj rekomendację" → tekst <10s cytujący nazwy nawyków
- [ ] 4.7 Production: odśwież → ostatnia rekomendacja widoczna
- [ ] 4.8 Production: konto bez danych → empty-state bez przycisku
- [ ] 4.9 Supabase Tables → `habits_recommendation` ma wpis z `grounded`
- [ ] 4.10 Render Logs — brak 5xx; log metryki `grounded`; brak wycieku klucza
