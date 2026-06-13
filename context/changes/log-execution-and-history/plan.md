# Log execution and history — plan implementacji

## Przegląd

Trzeci wycinek z mapy drogowej (S-03 `log-execution-and-history`). Wprowadza logowanie wykonań nawyków: toggle „wykonane dziś" jednym kliknięciem (HTMX, bez przeładowania, NFR <200ms) oraz read-only widok historii 30 dni jako wspólna siatka (aktywne nawyki × 30 dni). Dostarcza FR-008, FR-009, FR-010 oraz NFR <200ms.

Twarda reguła domeny (FR-009 + CLAUDE.md): **brak backdatingu** — logować/cofać można wyłącznie bieżący dzień. Egzekwowane z konstrukcji: jedyny endpoint mutujący operuje na `timezone.localdate()`, nigdy nie przyjmuje parametru daty; historia jest wyłącznie do odczytu.

Per-user isolation (CLAUDE.md hard rule) jest tu load-bearing po raz drugi: wykonania filtrujemy przez `habit__user=request.user`, dziedzicząc wzorzec `get_object_or_404(..., user=...)` / queryset-filtering z S-02.

## Analiza stanu obecnego

Z bezpośredniej inspekcji bazy kodu (S-02 budowany w tej samej sesji) + roadmap.md (S-03) + PRD:

- `habits/` app (S-02, zarchiwizowany) ma gotowy wzorzec: `models.py` (`Habit` + `HabitManager.active(user)` → `filter(user=user, archived=False).order_by('created_at')`), `admin.py` (`HabitAdmin` z `@admin.register`), `views.py` (Create/Update/Archive z `LoginRequiredMixin` + `get_queryset`/`get_object_or_404(user=...)`), `urls.py` (`app_name="habits"`: add/edit/archive), `forms.py`, `tests.py` (klasy z `@override_settings(SECURE_SSL_REDIRECT=False)`, stała `STRONG_PASSWORD`).
- `accounts/views.py:DashboardView` to `LoginRequiredMixin + TemplateView`; `get_context_data` już importuje `from habits.models import Habit` i wstawia `context["habits"] = Habit.objects.active(self.request.user)`.
- `templates/accounts/dashboard.html` listuje aktywne nawyki (`{% if habits %}` → `<ul>` z linkami Edytuj/Archiwizuj + „Dodaj kolejny"; `{% else %}` empty-state).
- `templates/base.html`: `<head>` ma Tailwind CDN (`<script src="https://cdn.tailwindcss.com">`, linia 7); kontener body to `max-w-md mx-auto` (448px) — **za wąski na siatkę 30 dni**.
- `habit_coach_ai/settings.py`: `TIME_ZONE = 'UTC'` (linia 127), `USE_TZ = True` (131), `LANGUAGE_CODE = 'pl'` (125), `DEFAULT_AUTO_FIELD = 'BigAutoField'` (161), `INSTALLED_APPS` zawiera `'habits'`.
- `habit_coach_ai/urls.py`: `path("habits/", include("habits.urls"))` już wpięte.
- Brak JS / HTMX w projekcie (`has_realtime: false`); całość server-rendered.
- Lekcja z `lessons.md`: success-criteria sign-off musi czytać faktyczny output (`check --deploy` = dokładnie W005+W021).

## Pożądany stan końcowy

Po wdrożeniu Phase 1-4:

- Zalogowany użytkownik na dashboardzie (`/`) przy każdym aktywnym nawyku widzi przycisk toggle „wykonane dziś"; jedno kliknięcie loguje wykonanie i wizualnie potwierdza bez przeładowania strony (HTMX swap, <200ms). Ponowne kliknięcie tego samego dnia cofa wpis (undo). Stan utrzymuje się po odświeżeniu.
- Backdating jest niemożliwy: brak jakiegokolwiek endpointu przyjmującego dowolną datę; toggle zawsze działa na `timezone.localdate()` (Europe/Warsaw).
- `/habits/history/` pokazuje read-only siatkę: wiersze = aktywne nawyki, kolumny = ostatnie 30 dni (włącznie z dziś), komórka oznaczona wykonane/niewykonane. Zarchiwizowane nawyki niewidoczne. Empty-states dla braku nawyków i braku logowań.
- Dashboard ma link do historii.
- Django admin pokazuje `HabitExecution` z filtrem po dacie i wyszukiwaniem po nazwie nawyku / emailu usera.
- ~14 testów Django zielonych pokrywających: toggle create/undo, today-only (data wpisu == dziś, brak endpointu na backdate), unique-per-day, cross-user 404 + isolation, historia (własne/aktywne/30 dni/empty), dashboard done-today context.
- `check --deploy` = dokładnie W005+W021. Prod smoke (Render+Supabase) end-to-end zielony, migracja `habits.0002` zastosowana.

### Kluczowe odkrycia

- **Brak backdatingu z konstrukcji, nie przez walidację**: zamiast endpointu „ustaw wykonanie na dzień X" z walidacją `X == today`, jest jeden endpoint toggle bez parametru daty — zawsze `localdate()`. To czyni FR-009 niewzruszalnym (nie ma czego obejść) i upraszcza testy. Past w historii jest read-only.
- **Obecność rekordu = wykonane**: `HabitExecution` nie ma pola boolean. Istnienie wiersza `(habit, date)` znaczy „wykonane"; undo = `DELETE` wiersza. `UniqueConstraint(habit, date)` zapobiega duplikatom dziennym.
- **HTMX bez nowej zależności Pythona**: HTMX to pojedynczy `<script>` z CDN (jak Tailwind). Endpoint rozróżnia żądanie HTMX od zwykłego nagłówkiem `HX-Request`: z HTMX → zwraca partial przycisku (swap); bez JS → `redirect` na dashboard (graceful degradation, pełny reload). Brak `django-htmx` w `pyproject.toml`.
- **CSRF dla HTMX**: `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'` na `<body>` w `base.html` — Django `CsrfViewMiddleware` akceptuje nagłówek `X-CSRFToken`. Bez tego POST z HTMX dostaje 403.
- **Done-today bez N+1**: `DashboardView` robi 1 dodatkowe zapytanie — `set(HabitExecution.objects.filter(habit__user=user, date=today).values_list('habit_id', flat=True))` — i anotuje każdy nawyk `h.done_today = h.pk in done_ids` w Pythonie. Historia: 1 zapytanie po wszystkich wykonaniach w oknie 30 dni, zbudowanie setu `(habit_id, date)`.
- **Szerokość kontenera**: siatka 30 kolumn nie mieści się w `max-w-md`. `base.html` dostaje `{% block container_width %}max-w-md{% endblock %}`; historia nadpisuje na szerszą (`max-w-4xl`) + `overflow-x-auto` na siatce dla mobile. Pozostałe strony bez zmian (domyślna wartość bloku).

## Czego NIE robimy

- **Backdated logging / undo wstecz** (FR-009) — tylko bieżący dzień; brak endpointu na inne daty. Historia czysto read-only.
- **Klikalna kolumna „dziś" w historii** — świadoma decyzja: toggle żyje wyłącznie na dashboardzie; historia to widok wzorca.
- **Historia nawyków zarchiwizowanych w UI** — siatka pokazuje tylko aktywne (spójnie z S-02 „archiwum ukryte z dashboardu"). Wykonania archiwalnych zostają w DB dla AI (S-04), ale nie są renderowane.
- **AI rekomendacje** (FR-011/013) — slice S-04. Tu tylko produkujemy dane (historia wykonań) jako źródło dla AI.
- **Streaki / liczniki / statystyki w UI** — siatka pokazuje surowe wykonane/niewykonane; logika streaków należy do S-04 (prompt assembly), nie tutaj.
- **Powiadomienia / przypomnienia o logowaniu** (PRD Non-Goals).
- **Per-user timezone** — projekt single-region; jedno `TIME_ZONE=Europe/Warsaw` dla wszystkich.
- **Graceful degradation ponad redirect** — bez JS toggle robi pełny POST→redirect; nie budujemy osobnego non-JS UI.
- **Edycja/usuwanie pojedynczych wykonań z admina jako flow użytkownika** — admin to tylko ops/debug.

## Podejście do implementacji

Czterofazowy plan w rytmie S-02: Phase 1 stawia dane (model + manager + admin + migracja) i ustawia strefę czasu; Phase 2 dodaje toggle endpoint + HTMX + integrację dashboardu; Phase 3 dorzuca read-only historię; Phase 4 weryfikuje pełną matrycą testów + deploy. Sekwencja topologiczna — Phase 2 zależy od modelu z Phase 1, Phase 3 reużywa partiala/wzorca z Phase 2.

Każda faza kończy się manualną bramką per `/10x-implement`. Phase 4 `check --deploy` MUSI zwracać dokładnie W005+W021 (lekcja retro).

## Krytyczne szczegóły implementacji

- **Sekwencja toggle (kolejność operacji)**: w `HabitToggleView.post` najpierw `get_object_or_404(Habit, pk=pk, user=request.user, archived=False)` (isolation + brak logowania na archiwum), potem `today = timezone.localdate()`, potem `delete()` jeśli wiersz istnieje albo `create()` jeśli nie. Zwróć partial ze stanem PO mutacji. Operacja na `localdate()` — nigdy na dacie z requestu.
- **Specyfikacja UX (HTMX swap)**: przycisk toggle jest samodzielnym partialem (`_toggle_button.html`) renderującym sam siebie z `hx-post` i `hx-swap="outerHTML"`; endpoint zwraca dokładnie ten sam partial w nowym stanie, więc swap podmienia przycisk in-place bez reloadu. Ten sam partial jest `{% include %}`-owany w pętli dashboardu — jedno źródło prawdy dla wyglądu i stanu.
- **Strefa czasu jako poprawność domeny**: po zmianie `TIME_ZONE='Europe/Warsaw'` wszystkie `timezone.localdate()` (views i testy) liczą „dziś" wg Warszawy. Testy asercji daty muszą też używać `timezone.localdate()`, nie `date.today()` (różnią się przy USE_TZ=True).

## Faza 1: HabitExecution model + manager + admin + migracja + TIME_ZONE

### Przegląd

Dodaj model `HabitExecution`, manager z helperami do done-today i historii, admin, ustaw `TIME_ZONE='Europe/Warsaw'`, wygeneruj i zastosuj migrację `0002`. Po tej fazie dane istnieją; brak UI.

### Wymagane zmiany

#### 1. HabitExecution model + HabitExecutionManager

**Plik**: `habits/models.py`

**Cel**: Model logu wykonania — obecność rekordu `(habit, date)` znaczy „wykonane". Manager eksponuje zapytania używane przez dashboard i historię, trzymając isolation w jednym miejscu (mirror „triplet rule" z S-02).

**Kontrakt**:
- `HabitExecutionManager(models.Manager)`:
  - `done_habit_ids_for(user, on_date)` → `set(self.filter(habit__user=user, date=on_date).values_list('habit_id', flat=True))` — dla done-today na dashboardzie.
  - `history_for(user, since_date)` → `self.filter(habit__user=user, habit__archived=False, date__gte=since_date)` — dla siatki historii (tylko aktywne nawyki).
- `HabitExecution(models.Model)`:
  - `habit = ForeignKey('habits.Habit', on_delete=CASCADE, related_name='executions')`
  - `date = DateField()`
  - `created_at = DateTimeField(auto_now_add=True)`
  - `objects = HabitExecutionManager()`
  - `class Meta`: `constraints = [UniqueConstraint(fields=['habit', 'date'], name='unique_execution_per_habit_day')]`, `ordering = ['-date']`
  - `__str__` → `f"{self.habit.name} @ {self.date}"`

#### 2. HabitExecutionAdmin

**Plik**: `habits/admin.py`

**Cel**: Ops/debug. Triplet completion.

**Kontrakt**: `@admin.register(HabitExecution)` z `list_display = ('habit', 'date', 'created_at')`, `list_filter = ('date',)`, `search_fields = ('habit__name', 'habit__user__email')`, `ordering = ('-date',)`.

#### 3. Ustaw strefę czasu

**Plik**: `habit_coach_ai/settings.py`

**Cel**: „Dziś" liczone wg strefy docelowych użytkowników (PL), nie UTC — poprawność FR-009 na granicy doby.

**Kontrakt**: `TIME_ZONE = 'UTC'` (linia 127) → `TIME_ZONE = 'Europe/Warsaw'`. `USE_TZ` zostaje `True`. Brak innych zmian.

#### 4. Wygeneruj i zastosuj migrację

**Plik**: `habits/migrations/0002_habitexecution.py` (wygenerowanie)

**Cel**: Tabela `habits_habitexecution` w SQLite + Postgres.

**Kontrakt**: `uv run python manage.py makemigrations habits` → `uv run python manage.py migrate`. Migracja `0002` z `CreateModel` (pola per kontrakt #1) + `UniqueConstraint unique_execution_per_habit_day`, zależna od `0001_initial`. Forward-only, brak destrukcyjnych operacji.

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py check` przechodzi bez warnings
- `uv run python manage.py makemigrations --check habits` zwraca „No changes detected" (po wygenerowaniu)
- `uv run python manage.py migrate` przechodzi
- Tabela `habits_habitexecution` istnieje w db.sqlite3

#### Weryfikacja ręczna

- `uv run python manage.py runserver` startuje bez błędu
- `/admin/` — sekcja „Habit executions" widoczna z list_display + filtrem po dacie
- Dodanie dwóch wykonań o tej samej `(habit, date)` przez admin → UniqueConstraint blokuje
- `uv run python manage.py shell` → `from django.utils import timezone; timezone.localdate()` zwraca datę wg Europe/Warsaw

**Uwaga implementacyjna**: Po automatycznej weryfikacji zatrzymaj się na ręczne potwierdzenie admina + strefy czasu przed Phase 2.

---

## Faza 2: Toggle endpoint + HTMX + integracja dashboardu

### Przegląd

Dodaj `HabitToggleView` (create/delete tylko dziś, isolation), URL `toggle`, partial przycisku, include HTMX w `base.html` (+ CSRF), rozszerz `DashboardView` o done-today i `dashboard.html` o przyciski toggle. Po tej fazie logowanie działa end-to-end lokalnie.

### Wymagane zmiany

#### 1. HabitToggleView

**Plik**: `habits/views.py`

**Cel**: Jeden endpoint toggle dla bieżącego dnia. Tworzy wpis jeśli brak, usuwa jeśli jest (undo). Isolation + brak logowania na archiwum. Zwraca partial dla HTMX albo redirect bez JS.

**Kontrakt**:
- `HabitToggleView(LoginRequiredMixin, View)`, tylko `post(self, request, pk)`:
  - `habit = get_object_or_404(Habit, pk=pk, user=request.user, archived=False)` — load-bearing isolation; cudzy/zarchiwizowany pk → 404.
  - `today = timezone.localdate()`.
  - `execution = HabitExecution.objects.filter(habit=habit, date=today).first()`; jeśli istnieje → `execution.delete()` (done=False); w przeciwnym razie `HabitExecution.objects.create(habit=habit, date=today)` (done=True).
  - Jeśli `request.headers.get("HX-Request")` → `render(request, "habits/_toggle_button.html", {"habit": habit, "done": <nowy stan>})`; w przeciwnym razie `redirect("accounts:dashboard")`.

#### 2. Toggle button partial

**Plik**: `templates/habits/_toggle_button.html` (nowy)

**Cel**: Samodzielny przycisk toggle reużywany przez dashboard (include) i endpoint (response). Renderuje stan done/not-done; HTMX podmienia in-place.

**Kontrakt**: `<button>` (lub `<form>` opakowujący) z `hx-post="{% url 'habits:toggle' habit.pk %}"`, `hx-swap="outerHTML"`, `hx-target` na samym sobie. Tailwind: stan done = wypełniony/zielony z „✓ Zrobione dziś"; not-done = obrys/neutralny z „Oznacz wykonane". Dostępność: `aria-pressed="{{ done }}"`.

#### 3. URL toggle

**Plik**: `habits/urls.py`

**Cel**: Wystawić endpoint pod namespace `habits`.

**Kontrakt**: dodać `path("<int:pk>/toggle/", views.HabitToggleView.as_view(), name="toggle")` do `urlpatterns`.

#### 4. Include HTMX + CSRF w base

**Plik**: `templates/base.html`

**Cel**: Udostępnić HTMX globalnie (jak Tailwind) i przekazać CSRF do wszystkich żądań HTMX.

**Kontrakt**: po linii Tailwind (7) w `<head>` dodać `<script src="https://unpkg.com/htmx.org@2">` (pin major). Na `<body>` dodać `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'`. Brak innych zmian w base poza blokiem szerokości (patrz Phase 3 #4 — można dodać teraz lub w Phase 3; preferowane Phase 3 razem z historią).

#### 5. DashboardView done-today

**Plik**: `accounts/views.py`

**Cel**: Dashboard wie, które aktywne nawyki są wykonane dziś, by przycisk renderował właściwy stan.

**Kontrakt**: w `DashboardView.get_context_data` po pobraniu `habits`: `today = timezone.localdate()`; `done_ids = HabitExecution.objects.done_habit_ids_for(self.request.user, today)`; dla każdego `h in habits` ustaw `h.done_today = h.pk in done_ids`. Wymaga importów `from django.utils import timezone` i `from habits.models import HabitExecution`. (`habits` może wymagać ewaluacji do listy, by anotacja przetrwała do template.)

#### 6. Dashboard: przyciski toggle

**Plik**: `templates/accounts/dashboard.html`

**Cel**: Przy każdym aktywnym nawyku pokazać toggle „wykonane dziś".

**Kontrakt**: w pętli `{% for habit in habits %}` dodać `{% include "habits/_toggle_button.html" with habit=habit done=habit.done_today %}` obok linków Edytuj/Archiwizuj. Layout pozostaje spójny (Tailwind). Bez zmian w empty-state.

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py check` przechodzi
- URL resolver pasuje `/habits/<int>/toggle/`
- Brak ImportError (`HabitExecution`, `timezone` w accounts/views.py)

#### Weryfikacja ręczna

- Dashboard zalogowanego: przy każdym nawyku przycisk „Oznacz wykonane"
- Klik → przycisk zmienia się na „✓ Zrobione dziś" bez przeładowania (HTMX swap), wizualnie <200ms
- Ponowny klik → wraca do „Oznacz wykonane" (undo); w DB brak wiersza
- Odświeżenie strony → stan utrzymany (rekord w DB)
- `/habits/<id>/toggle/` POST jako NIE-owner → 404; na zarchiwizowanym nawyku → 404
- Z wyłączonym JS: POST formularza toggle → redirect na dashboard (fallback działa)

**Uwaga implementacyjna**: Po manualnej weryfikacji happy-path + isolation 404, zatrzymaj się przed Phase 3.

---

## Faza 3: Read-only widok historii 30 dni

### Przegląd

Dodaj `HabitHistoryView` + template siatki (aktywne nawyki × 30 dni), URL `history`, blok szerokości w `base.html`, link z dashboardu, empty-states. Po tej fazie pełny UX S-03 działa lokalnie.

### Wymagane zmiany

#### 1. HabitHistoryView

**Plik**: `habits/views.py`

**Cel**: Read-only siatka 30 dni dla aktywnych nawyków zalogowanego usera. Bez N+1.

**Kontrakt**:
- `HabitHistoryView(LoginRequiredMixin, TemplateView)`, `template_name = "habits/history.html"`.
- `get_context_data`: `today = timezone.localdate()`; `start = today - timedelta(days=29)` (30 dni włącznie); `days = [start + timedelta(d) for d in range(30)]`; `habits = list(Habit.objects.active(user))`; `done = set(HabitExecution.objects.history_for(user, start).values_list('habit_id', 'date'))`. Zbuduj w Pythonie `rows = [{"habit": h, "cells": [{"date": d, "done": (h.pk, d) in done} for d in days]} for h in habits]`. Wstaw `rows`, `days` do kontekstu.

#### 2. History template (siatka)

**Plik**: `templates/habits/history.html` (nowy)

**Cel**: Renderować siatkę wzorca + empty-states. Spójny Tailwind.

**Kontrakt**: extends `base.html`, nadpisuje `{% block container_width %}max-w-4xl{% endblock %}`. `<h1>Historia (30 dni)</h1>`. `{% if rows %}` → `<div class="overflow-x-auto">` z `<table>`: nagłówek = daty (kompaktowo, np. dzień miesiąca), wiersze = nawyki (`{{ row.habit.name }}` + komórki: done → wypełniona/✓, not-done → pusta). Dziś wyróżniony. `{% else %}` → empty-state „Nie masz aktywnych nawyków" z linkiem `{% url 'habits:add' %}`. Gdy są nawyki ale zero wykonań — siatka renderuje się z samymi pustymi komórkami (naturalnie, bez osobnej gałęzi) + opcjonalny hint „Zacznij logować na dashboardzie".

#### 3. Blok szerokości w base

**Plik**: `templates/base.html`

**Cel**: Pozwolić historii być szerszą bez zmiany pozostałych stron.

**Kontrakt**: kontener `<div class="max-w-md mx-auto ...">` → `<div class="{% block container_width %}max-w-md{% endblock %} mx-auto ...">`. Domyślna wartość `max-w-md` zachowuje wygląd login/register/dashboard/form.

#### 4. Link do historii z dashboardu

**Plik**: `templates/accounts/dashboard.html`

**Cel**: Nawigacja do widoku historii.

**Kontrakt**: dodać link `<a href="{% url 'habits:history' %}">Historia</a>` (widoczny gdy są nawyki; Tailwind spójny). Nie dotykać empty-state ani przycisków toggle.

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py check` przechodzi bez „template does not exist"
- `uv run python manage.py collectstatic --no-input --dry-run` przechodzi
- URL resolver pasuje `/habits/history/`

#### Weryfikacja ręczna

- `/habits/history/` zalogowany z nawykami → siatka aktywne × 30 dni; dzisiejsze wykonania (z Phase 2) oznaczone
- Zarchiwizowany nawyk NIE pojawia się w siatce
- Świeży user bez nawyków → empty-state z linkiem do `/habits/add/`
- User z nawykami bez logowań → siatka z pustymi komórkami
- Na mobile/wąsko → siatka scrolluje poziomo (overflow-x-auto), reszta stron bez zmian szerokości
- Link „Historia" na dashboardzie prowadzi do `/habits/history/`

**Uwaga implementacyjna**: Po pełnej manualnej weryfikacji lokalnie, zatrzymaj się przed Phase 4.

---

## Faza 4: Testy (pełna matryca) + deployment verify

### Przegląd

Napisz `habits/tests.py` (dopisanie klas dla toggle i historii), dopisz test done-today do `accounts/tests.py`, re-verify `check --deploy`, commit + push (Render auto-deploy migracji `0002`). Po tej fazie S-03 produkcyjnie zielony.

### Wymagane zmiany

#### 1. Testy toggle + model + historia

**Plik**: `habits/tests.py`

**Cel**: Pokryć FR-008/009/010 + pełną matrycę isolation + regułę „tylko dziś". Klasy z `@override_settings(SECURE_SSL_REDIRECT=False)`.

**Kontrakt**: Klasy:
- `HabitToggleViewTests(TestCase)`:
  - `test_toggle_creates_execution_for_today` (POST → wiersz `(habit, localdate())` istnieje; data == `timezone.localdate()`)
  - `test_toggle_twice_removes_execution` (undo — drugi POST usuwa wiersz, brak duplikatu)
  - `test_toggle_htmx_returns_partial_with_new_state` (nagłówek `HX-Request` → 200 + treść partiala odzwierciedla stan)
  - `test_toggle_without_htmx_redirects_to_dashboard` (brak nagłówka → 302 na dashboard)
  - `test_toggle_rejects_other_users_habit_with_404`
  - `test_toggle_rejects_archived_habit_with_404`
  - `test_toggle_requires_login`
- `HabitExecutionModelTests(TestCase)`:
  - `test_unique_constraint_blocks_duplicate_per_day` (dwa `create` na `(habit, date)` → `IntegrityError`)
- `HabitExecutionManagerTests(TestCase)`:
  - `test_done_habit_ids_for_returns_only_users_executions_on_date` (isolation queryset-level)
  - `test_history_for_excludes_archived_and_other_users_and_old`
- `HabitHistoryViewTests(TestCase)`:
  - `test_history_shows_grid_for_own_active_habits` (rows zawiera aktywne; oznaczone wykonania w oknie)
  - `test_history_excludes_archived_habits`
  - `test_history_excludes_other_users_habits`
  - `test_history_empty_state_when_no_habits`
  - `test_history_requires_login`

#### 2. DashboardView done-today test

**Plik**: `accounts/tests.py`

**Cel**: Dashboard anotuje `done_today` poprawnie i tylko dla własnych wykonań.

**Kontrakt**: dodać do `DashboardViewTests`:
- `test_dashboard_marks_habit_done_today` — utwórz wykonanie dziś dla nawyku usera A; GET `/` jako A; sprawdź że odpowiadający `habit.done_today` jest `True`, a nawyk bez wykonania `False`.

#### 3. Commit + push

**Cel**: Push triggeruje Render auto-deploy z migracją `habits.0002` na Supabase.

**Kontrakt**: commity per faza (jak S-02), push do `origin/main`. Render auto-deploys; `preDeployCommand` migruje.

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py test habits` — wszystkie zielone (~14 nowych metod + istniejące z S-02)
- `uv run python manage.py test accounts` — zielone (poprzednie + 1 nowy)
- `uv run python manage.py test` — green
- `uv run python manage.py check --deploy` (DEBUG=False, klucz+ALLOWED_HOSTS) — dokładnie 2 warningi (W005, W021), nic więcej
- Render deploy log: `Applying habits.0002... OK` + service `live`

#### Weryfikacja ręczna

- Production: zaloguj → dashboard, toggle „wykonane dziś" działa (HTMX, bez reloadu)
- Production: undo działa; stan utrzymany po odświeżeniu
- Production: `/habits/history/` pokazuje siatkę z dzisiejszym wpisem
- Production: `/habits/<cudzy_id>/toggle/` → 404
- Supabase Tables → `habits_habitexecution` ma wpis z poprawną datą
- Render Logs — brak 5xx po smoke

**Uwaga implementacyjna**: Po zielonym prod deploy + smoke, S-03 gotowy do `/10x-impl-review log-execution-and-history` przed `/10x-archive`.

---

## Strategia testowania

### Testy jednostkowe

- ~14 metod w `habits/tests.py` + 1 w `accounts/tests.py`. Pokrywają FR-008 (toggle create), FR-009 (undo today, brak backdate — data wpisu == localdate, brak endpointu na inną datę), FR-010 (historia 30 dni), unique-per-day, pełną matrycę per-user isolation (toggle 404 cross-user + archived; manager queryset-level; historia własne/aktywne).
- Każda klasa z `@override_settings(SECURE_SSL_REDIRECT=False)`; stała `STRONG_PASSWORD`.
- Asercje daty przez `timezone.localdate()` (nie `date.today()`) — USE_TZ=True + Europe/Warsaw.

### Testy integracyjne

- Pełny flow toggle (create→undo) + historia pokryte kombinacją testów HTTP (`HX-Request` i bez).
- Production smoke (manual) potwierdza end-to-end z migracją `0002` na Supabase.

### Kroki testowania ręcznego

1. Lokalnie: `runserver` → dashboard → toggle nawyku → „✓ Zrobione dziś" bez reloadu → odśwież → stan utrzymany.
2. Lokalnie: toggle ponownie → undo → komórka pusta.
3. Lokalnie: `/habits/history/` → siatka z dzisiejszym wpisem; zarchiwizowany nawyk nieobecny.
4. Lokalnie: drugi user → `/habits/<id_pierwszego>/toggle/` POST → 404.
5. Lokalnie: wyłącz JS → toggle robi redirect (fallback).
6. Production: powtórz 1-3 na onrender.com.
7. Production: Supabase Tables → `habits_habitexecution` ma wpis.

## Uwagi dotyczące wydajności

NFR <200ms na toggle: endpoint robi 1 lookup nawyku (isolation) + 1 zapytanie o wykonanie + 1 delete/create, zwraca mały partial — bez pełnego renderu strony. HTMX swap podmienia tylko przycisk. Dashboard: 2 zapytania (habits + done-today set). Historia: 2 zapytania (habits + executions w oknie), budowa siatki w Pythonie — brak N+1. Skala MVP (mały wolumen) bez twardych budżetów poza FR-008 <200ms.

## Uwagi dotyczące migracji

`habits.0002_habitexecution` zależy od `0001_initial` (FK do `Habit`). Brak istniejących danych do migracji (fresh model). Forward-only, brak destrukcyjnych operacji. `on_delete=CASCADE` na `habit`: usunięcie nawyku usuwa jego wykonania — spójne (archiwizacja, nie delete, jest ścieżką MVP; hard delete poza zakresem). Zmiana `TIME_ZONE` nie wymaga migracji danych (USE_TZ=True przechowuje UTC w DB; `DateField` na wykonaniach to data lokalna liczona przy zapisie).

## Referencje

- Powiązane wycinki: `context/foundation/roadmap.md` (S-03)
- Twarde reguły: `CLAUDE.md` (per-user isolation, brak backdatingu), PRD FR-008/009/010, NFR <200ms
- Lekcje: `context/foundation/lessons.md` (success-criteria sign-off; validate_unique — choć tu unikalność jest na polach modelu, nie formularza)
- Wzorzec per-app: `context/archive/2026-06-07-manage-habits/` (S-02) + `habits/` w bazie kodu
- HTMX: `https://htmx.org/docs/` (hx-post, hx-swap, HX-Request, CSRF via hx-headers)
- Django: `timezone.localdate()` — `https://docs.djangoproject.com/en/6.0/ref/utils/#django.utils.timezone.localdate`

## Progress

> Konwencja: `- [ ]` oczekujące, `- [x]` wykonane. Dodaj ` — <commit sha>`, gdy krok zostanie zrealizowany. Nie zmieniaj nazw tytułów kroków. Zobacz `references/progress-format.md`.

### Faza 1: HabitExecution model + manager + admin + migracja + TIME_ZONE

#### Automatyczne

- [x] 1.1 `manage.py check` przechodzi bez warnings — 02adc03
- [x] 1.2 `manage.py makemigrations --check habits` zwraca „No changes detected" po wygenerowaniu — 02adc03
- [x] 1.3 `manage.py migrate` przechodzi — 02adc03
- [x] 1.4 Tabela `habits_habitexecution` istnieje w db.sqlite3 — 02adc03

#### Ręczne

- [x] 1.5 `runserver` startuje bez błędu — 02adc03
- [x] 1.6 `/admin/` — sekcja „Habit executions" z list_display + filtrem po dacie — 02adc03
- [x] 1.7 Duplikat `(habit, date)` przez admin → UniqueConstraint blokuje — 02adc03
- [x] 1.8 `timezone.localdate()` w shell zwraca datę wg Europe/Warsaw — 02adc03

### Faza 2: Toggle endpoint + HTMX + integracja dashboardu

#### Automatyczne

- [x] 2.1 `manage.py check` przechodzi — bf96ddc
- [x] 2.2 URL resolver pasuje `/habits/<int>/toggle/` — bf96ddc
- [x] 2.3 Brak ImportError (`HabitExecution`, `timezone` w accounts/views.py) — bf96ddc

#### Ręczne

- [x] 2.4 Dashboard: przycisk „Oznacz wykonane" przy każdym nawyku — bf96ddc
- [x] 2.5 Klik → „✓ Zrobione dziś" bez reloadu (HTMX swap), <200ms — bf96ddc
- [x] 2.6 Ponowny klik → undo; w DB brak wiersza — bf96ddc
- [x] 2.7 Odświeżenie → stan utrzymany — bf96ddc
- [x] 2.8 Toggle jako NIE-owner → 404; na zarchiwizowanym → 404 — bf96ddc
- [x] 2.9 Bez JS → toggle robi redirect na dashboard (fallback) — bf96ddc

### Faza 3: Read-only widok historii 30 dni

#### Automatyczne

- [x] 3.1 `manage.py check` przechodzi bez „template does not exist" — 964bbc5
- [x] 3.2 `manage.py collectstatic --no-input --dry-run` przechodzi — 964bbc5
- [x] 3.3 URL resolver pasuje `/habits/history/` — 964bbc5

#### Ręczne

- [x] 3.4 `/habits/history/` → siatka aktywne × 30 dni; dzisiejsze wpisy oznaczone — 964bbc5
- [x] 3.5 Zarchiwizowany nawyk nieobecny w siatce — 964bbc5
- [x] 3.6 Świeży user bez nawyków → empty-state z linkiem do `/habits/add/` — 964bbc5
- [x] 3.7 User z nawykami bez logowań → siatka z pustymi komórkami — 964bbc5
- [x] 3.8 Mobile/wąsko → siatka scrolluje poziomo; reszta stron bez zmian szerokości — 964bbc5
- [x] 3.9 Link „Historia" na dashboardzie → `/habits/history/` — 964bbc5

### Faza 4: Testy (pełna matryca) + deployment verify

#### Automatyczne

- [x] 4.1 `manage.py test habits` — wszystkie zielone (28: 13 S-02 + 15 nowych)
- [x] 4.2 `manage.py test accounts` — zielone (9: 8 + 1 nowy)
- [x] 4.3 `manage.py test` (całość) — green (37)
- [x] 4.4 `manage.py check --deploy` (DEBUG=False) — dokładnie 2 warningi (W005, W021)
- [ ] 4.5 Render deploy log: `Applying habits.0002... OK` + service `live`

#### Ręczne

- [ ] 4.6 Production: toggle „wykonane dziś" działa (HTMX, bez reloadu)
- [ ] 4.7 Production: undo działa; stan utrzymany po odświeżeniu
- [ ] 4.8 Production: `/habits/history/` pokazuje siatkę z dzisiejszym wpisem
- [ ] 4.9 Production: `/habits/<cudzy_id>/toggle/` → 404
- [ ] 4.10 Supabase Tables → `habits_habitexecution` ma wpis z poprawną datą
- [ ] 4.11 Render Logs — brak 5xx po smoke
