# Manage habits — plan implementacji

## Przegląd

Drugi wycinek z mapy drogowej (S-02 `manage-habits`). Wprowadza CRUD-bez-delete dla nawyków zalogowanego użytkownika: dodanie z nazwą (codzienne — częstotliwości złożone Parked), edycję nazwy, archiwizację z zachowaniem historii. Dostarcza FR-005, FR-006, FR-007 oraz wypełnia empty-state CTA z S-01 (link `href="#"` w `templates/accounts/dashboard.html:14` z TODO komentarzem).

Pełni rolę pierwszego "domain" app — to tutaj per-user isolation (CLAUDE.md hard rule) staje się load-bearing po raz pierwszy w projekcie. Wzorzec queryset filtering ustanowiony w tym slice'ie dziedziczą S-03 (logging) i S-04 (AI rec).

## Analiza stanu obecnego

Z bezpośredniej inspekcji `accounts/` + roadmap.md (zaktualizowane 2026-06-07) + dzisiejszego retro:

- `accounts/` (S-01) zarchiwizowany — gotowy wzorzec per-app: `models.py` (User + UserManager), `admin.py` (CustomUserAdmin), `forms.py` (CustomUserCreationForm), `views.py` (RegisterView, DashboardView), `urls.py` (`app_name="accounts"`), `tests.py` (3 klasy z `@override_settings(SECURE_SSL_REDIRECT=False)`).
- `templates/accounts/dashboard.html` ma placeholder CTA `<a href="#" ...>Dodaj swój pierwszy nawyk</a>` na linii 14, z komentarzem `<!-- TODO: S-02 — point href to {% url 'habits:add' %} -->`.
- `DashboardView` (`accounts/views.py:20`) to `LoginRequiredMixin + TemplateView`; aktualnie nie ma kontekstu z habits.
- `habit_coach_ai/urls.py:10-12` — wzór wpinania apps: `path("admin/", ...)`, `path("accounts/", include("django.contrib.auth.urls"))`, `path("", include("accounts.urls"))`.
- `habit_coach_ai/settings.py:42` — INSTALLED_APPS rozszerzona o `"accounts"`; dodanie `"habits"` to jedna linia.
- Lekcja z retro: `success-criteria sign-off must actually read the command output` (`context/foundation/lessons.md`) — Phase 4 `check --deploy` musi zwracać 0 dodatkowych warningów (poza opt-in W005/W021 HSTS preload).
- Brak istniejących data models poza User; brak migracji habits — fresh slate (zarówno lokalny SQLite jak i Supabase Postgres).
- Tailwind CDN aktywny przez `templates/base.html:7`; styling spójny z S-01 — używamy tych samych klas `max-w-md mx-auto` itp.

## Pożądany stan końcowy

Po wdrożeniu Phase 1-4:

- Zalogowany użytkownik na `/` (DashboardView):
  - Pustym koncie: widzi empty-state CTA "Dodaj swój pierwszy nawyk" → link do `/habits/add/`.
  - Z nawykami: widzi listę aktywnych (sortowaną po `created_at` ASC), każdy z nazwą i akcjami "Edytuj" / "Archiwizuj"; przycisk "Dodaj kolejny" → `/habits/add/`.
- `/habits/add/` (GET): formularz `name`; (POST): tworzy `Habit(user=request.user)`, redirect `/`.
- `/habits/<id>/edit/` (GET): formularz pre-filled; (POST): aktualizuje nazwę; cudzy `<id>` → 404.
- `/habits/<id>/archive/` (GET): strona confirm "Na pewno chcesz zarchiwizować '<name>'? Historia zostanie zachowana."; (POST): ustawia `archived=True`, redirect `/`; cudzy `<id>` → 404.
- Zarchiwizowane nawyki są niewidoczne na dashbordzie (filter `archived=False`).
- Django admin pokazuje `Habit` z `list_display=('name', 'user', 'archived', 'created_at')` i filtrem po user/archived.
- 10+ testów Django w `habits/tests.py` przechodzi zielono, pokrywających pełny cross-user matrix per-user isolation.
- Local + Production smoke: rejestracja nowego konta → dodanie nawyku → edycja → archiwizacja działa end-to-end.

### Kluczowe odkrycia

- **Cross-app dependency**: `DashboardView` (w `accounts/`) musi pobrać `Habit.objects.active(request.user)` — to tworzy unidirectional import `accounts.views → habits.models`. Akceptowalne; `accounts/` jest "auth shell" a habits to first domain. Nie odwracamy w drugą stronę.
- **Unique constraint na (user, name)**: implementowane przez `Habit.Meta.constraints = [UniqueConstraint(fields=['user', 'name'], name='unique_habit_name_per_user')]`. Form rzuca `ValidationError`; test `test_rejects_duplicate_name`.
- **`get_queryset()` jako load-bearing wzorzec**: każdy z `HabitUpdateView`/`HabitArchiveView` overridu'je `get_queryset()` zwracając `Habit.objects.filter(user=self.request.user)`. Django's generic `get_object_or_404` na tym querysecie automatycznie zwraca 404 dla cudzych `<id>` — testowane explicit.
- **`HabitManager.active(user)` helper**: queryset `filter(user=user, archived=False).order_by('created_at')`. Eksponuje wzorzec do reuse w S-03 (logging musi też filtrować aktywne nawyki).
- **`HabitArchiveView` jako `View.dispatch`**: nie używamy `DeleteView` (myli semantykę — to NIE delete). Custom view z `get()` (renderuje confirm template) i `post()` (ustawia `archived=True` + redirect).
- **Triplet rule (Model + Manager + Admin)** z retro F3: `Habit` dostaje swój `HabitManager`, `HabitAdmin`. Brak takiej fragmentacji jak w pierwotnym planie S-01 — wszystko od razu jako triplet.

## Czego NIE robimy

- **Logowanie wykonań** (FR-008) — slice S-03, kolejny. Model `HabitExecution` nie powstaje teraz.
- **Hard delete** nawyku z historią (PRD §Non-Goals) — tylko archive. Brak ścieżki delete w UI ani API.
- **Un-archive z UI** — zarchiwizowane są kompletnie ukryte; przywrócenie wymaga Django admin lub SQL. Świadomy tradeoff (decyzja "Zupełnie ukryte z dashboardu").
- **Częstotliwości inne niż codzienna** ("N razy w tygodniu", "tylko dni robocze") — PRD §Non-Goals; wszystkie nawyki są codzienne. Brak pola `frequency` w modelu.
- **AI rekomendacje** (FR-011/013) — slice S-04. Habit jako data source dla AI istnieje po tym slice'ie, ale nic nie generujemy.
- **Inline edit na dashbordzie** — decyzja "osobne URLs"; edycja przez `/habits/<id>/edit/`.
- **Bulk actions** (archiwizuj wszystkie, restore wszystkie) — out of scope; per-row tylko.
- **Habit categories / tags / colors** — nie ma user story.
- **Inline reorder / drag-and-drop sortowanie** — fixed `created_at` ASC.
- **Soft archive z undo timer** — świadomy tradeoff (decyzja "confirm page"), MVP nie potrzebuje.

## Podejście do implementacji

Czterofazowy plan w rytmie S-01: Phase 1 stawia foundation (app + model + admin + migration), Phase 2 dodaje views + URLs + dashboard rewire, Phase 3 dorzuca templates (form, confirm, dashboard rewrite), Phase 4 weryfikuje pełnym testowym matrix per-user isolation + manual smoke. Sekwencja topologiczna — Phase 1 fail blokuje Phase 2, Phase 3 zależy od URLs z Phase 2.

Każda faza kończy się manual gate per `/10x-implement` workflow z M2L2. Phase 4 success criterion `check --deploy` MUSI zwracać dokładnie 2 warningi (W005, W021 — opt-in HSTS preload), zgodnie z lekcją z retro 2026-06-07.

## Krytyczne szczegóły implementacji

- **Kolejność migracji**: `habits.0001_initial` zależy od `accounts.User` przez FK. Django auto-resolves dependency przez `AUTH_USER_MODEL = 'accounts.User'` (już w settings.py:45). Lokalny SQLite ma `accounts_user` z S-01; Supabase też (deploy zielony od 2026-06-07). Brak ryzyka kolizji migracji.
- **`get_queryset()` w UpdateView i ArchiveView**: Django's generic `SingleObjectMixin.get_object()` woła `self.get_queryset()` *przed* lookup po pk. Filtrowanie po `user=request.user` na poziomie querysetu jest jedynym poprawnym miejscem — sprawdzanie `if habit.user != request.user: raise Http404` w `get_object()` lub `dispatch()` to anti-pattern (race-prone, łatwo zapomnieć przy następnym view).

## Faza 1: Habits app + Habit model + UserManager + admin + migration

### Przegląd

Stwórz `habits/` app z modelem `Habit` (name, user FK, archived, created_at), `HabitManager.active()` helper, custom admin, zarejestruj w INSTALLED_APPS, wygeneruj i zastosuj migrację. Po tej fazie Django wie o modelu, admin pokazuje habits z filtrem.

### Wymagane zmiany

#### 1. Utwórz aplikację `habits/`

**Plik**: (powstanie cały katalog `habits/`)

**Cel**: Zapewnić dedykowaną przestrzeń dla habit-related models, views, templates per Django convention. Mirror `accounts/` shape.

**Kontrakt**: `uv run python manage.py startapp habits` w cwd. Powstaje `habits/__init__.py`, `habits/admin.py`, `habits/apps.py`, `habits/migrations/__init__.py`, `habits/models.py`, `habits/tests.py`, `habits/views.py`.

#### 2. Habit model + HabitManager

**Plik**: `habits/models.py`

**Cel**: Model `Habit` z load-bearing per-user isolation jako manager method. Mirror "triplet rule" (Model + Manager + Admin) z lekcji retro.

**Kontrakt**:
- `HabitManager(models.Manager)` z metodą `active(user)` → `self.filter(user=user, archived=False).order_by('created_at')`.
- `Habit(models.Model)` z polami:
  - `name = CharField(max_length=100)` (strip whitespace via form `clean_name`)
  - `user = ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name='habits')`
  - `archived = BooleanField(default=False)`
  - `created_at = DateTimeField(auto_now_add=True)`
- `objects = HabitManager()`
- `class Meta`: `constraints = [UniqueConstraint(fields=['user', 'name'], name='unique_habit_name_per_user')]`, `ordering = ['created_at']`
- `__str__` zwraca `self.name`

#### 3. HabitAdmin

**Plik**: `habits/admin.py`

**Cel**: Ops/debug tool dla superuser. Triplet completion.

**Kontrakt**: `@admin.register(Habit)` z `HabitAdmin(admin.ModelAdmin)` definiującym `list_display = ('name', 'user', 'archived', 'created_at')`, `list_filter = ('archived', 'created_at')`, `search_fields = ('name', 'user__email')`, `ordering = ('-created_at',)`.

#### 4. Zarejestruj w INSTALLED_APPS

**Plik**: `habit_coach_ai/settings.py`

**Cel**: Django ma wiedzieć o nowym appie żeby app config się załadował i migracje były odkryte.

**Kontrakt**: `INSTALLED_APPS` rozszerzona o `"habits"` po `"accounts"`. Brak innych zmian w settings.

#### 5. Apps config (default_auto_field parity)

**Plik**: `habits/apps.py`

**Cel**: Wpisać `default_auto_field` zgodnie z idiomatic startapp output (mimo że projekt ma global `DEFAULT_AUTO_FIELD`). Spójność z accounts/apps.py (jeśli ten też ma — sprawdzić w implementacji).

**Kontrakt**: `class HabitsConfig(AppConfig)` z `default_auto_field = 'django.db.models.BigAutoField'`, `name = 'habits'`. To jest domyślny output `startapp`, więc minimalnie do dotknięcia.

#### 6. Wygeneruj i zastosuj migrację

**Plik**: `habits/migrations/0001_initial.py` (wygenerowanie)

**Cel**: Stworzyć tabelę `habits_habit` w SQLite + Postgres.

**Kontrakt**: Sekwencja: `uv run python manage.py makemigrations habits` → `uv run python manage.py migrate`. Wygenerowana migracja `0001_initial` powinna mieć `CreateModel` z polami zgodnymi z kontraktem #2 oraz `AddConstraint` dla `unique_habit_name_per_user`.

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py check` przechodzi bez warnings
- `uv run python manage.py makemigrations --check habits` zwraca "No changes detected" (po wygenerowaniu migracji)
- `uv run python manage.py migrate` przechodzi
- Tabela `habits_habit` istnieje w db.sqlite3

#### Weryfikacja ręczna

- `uv run python manage.py runserver` startuje bez błędu
- `/admin/` — superuser widzi sekcję "Habits" → "Habits" z możliwością dodania (test poprzez admin); list_display + filter widoczne
- Dodanie nawyku z duplikatem nazwy (same user, same name) przez admin → walidacja blokuje (UniqueConstraint)

**Uwaga implementacyjna**: Po pomyślnym przejściu automatycznej weryfikacji, zatrzymaj się tutaj na ręczne potwierdzenie, że admin działa, zanim przejdziesz do Phase 2.

---

## Faza 2: Views + URL wiring + DashboardView update

### Przegląd

Dodaj `HabitCreateView`, `HabitUpdateView`, `HabitArchiveView` z load-bearing per-user querysetem; podłącz pod namespace `habits` w `/habits/`. Update `DashboardView` w accounts żeby pobierał habits do contextu. Po tej fazie URLs odpowiadają HTML-em (bez templates Phase 3 będą TemplateDoesNotExist — to OK).

### Wymagane zmiany

#### 1. HabitForm

**Plik**: `habits/forms.py` (nowy)

**Cel**: Django Form dla create + update (jeden form, dwa views go używają). Strip whitespace na `name`.

**Kontrakt**: `HabitForm(forms.ModelForm)` z `class Meta: model = Habit; fields = ['name']`. Override `clean_name(self)` → `return self.cleaned_data['name'].strip()`. `UniqueConstraint` z modelu daje błąd na duplikatach automatycznie (Django ModelForm wywoła `validate_unique` → `ValidationError`).

#### 2. HabitCreateView + HabitUpdateView + HabitArchiveView

**Plik**: `habits/views.py`

**Cel**: Trzy views obsługujące dodawanie, edycję i archiwizację. Każdy `LoginRequiredMixin`. Update/Archive overridu'ją `get_queryset()` żeby cudzy `<id>` → 404 (load-bearing per CLAUDE.md hard rule).

**Kontrakt**:
- `HabitCreateView(LoginRequiredMixin, CreateView)`:
  - `form_class = HabitForm`
  - `template_name = "habits/habit_form.html"`
  - `success_url = reverse_lazy("accounts:dashboard")`
  - Override `form_valid(self, form)`: ustaw `form.instance.user = self.request.user` przed `super().form_valid(form)`.
- `HabitUpdateView(LoginRequiredMixin, UpdateView)`:
  - `form_class = HabitForm`
  - `template_name = "habits/habit_form.html"`
  - `success_url = reverse_lazy("accounts:dashboard")`
  - Override `get_queryset(self)`: `return Habit.objects.filter(user=self.request.user)` — load-bearing isolation.
- `HabitArchiveView(LoginRequiredMixin, View)`:
  - `get(self, request, pk)`: lookup `habit = get_object_or_404(Habit, pk=pk, user=request.user)`; render `habits/habit_confirm_archive.html` z `{"habit": habit}`.
  - `post(self, request, pk)`: lookup same, ustaw `habit.archived = True`, `habit.save(update_fields=['archived'])`, redirect `accounts:dashboard`.

#### 3. habits/urls.py

**Plik**: `habits/urls.py` (nowy)

**Cel**: Wystawić CRUD endpoints pod namespace `habits`.

**Kontrakt**:
```
app_name = "habits"
urlpatterns = [
    path("add/", views.HabitCreateView.as_view(), name="add"),
    path("<int:pk>/edit/", views.HabitUpdateView.as_view(), name="edit"),
    path("<int:pk>/archive/", views.HabitArchiveView.as_view(), name="archive"),
]
```

#### 4. Include habits URLs w project urls.py

**Plik**: `habit_coach_ai/urls.py`

**Cel**: Wystawić namespace `habits` pod `/habits/`.

**Kontrakt**: Dodać `path("habits/", include("habits.urls"))` między `accounts/` (line 11) a `""` include (line 12).

#### 5. Update DashboardView w accounts/

**Plik**: `accounts/views.py`

**Cel**: Dashboard ma pokazywać listę aktywnych nawyków zalogowanego usera (kontekst dla template Phase 3).

**Kontrakt**: `DashboardView` dostaje override `get_context_data(self, **kwargs)`: rozszerzyć super context o `"habits": Habit.objects.active(self.request.user)`. Wymaga `from habits.models import Habit` na górze pliku. Filter `active()` (z HabitManager) gwarantuje `archived=False` + ordering.

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py check` przechodzi
- URL resolver pasuje endpointy: `/habits/add/`, `/habits/<int>/edit/`, `/habits/<int>/archive/`
- Brak ImportError (`from habits.models import Habit` w accounts/views.py rozwiązuje się)

#### Weryfikacja ręczna

- `/habits/add/` GET (zalogowany) → 200 lub TemplateDoesNotExist dla `habits/habit_form.html` (OK — Phase 3 dodaje template)
- `/habits/<istniejący>/edit/` (zalogowany jako owner) → 200 lub TemplateDoesNotExist (OK)
- `/habits/<id>/edit/` (zalogowany jako NIE-owner) → 404 (load-bearing isolation działa zanim templates istnieją)
- `/` jako zalogowany z superuser (z Phase 1 testu admin) — TemplateDoesNotExist albo render starego dashboardu z `habits` w context (Phase 3 to wykorzysta)

**Uwaga implementacyjna**: Po automatycznej weryfikacji, ręcznie potwierdź że cross-user 404 działa (np. utwórz drugiego superusera, zaloguj się jako on, próbuj `/habits/<id>/edit/` z id pierwszego) zanim przejdziesz do Phase 3.

---

## Faza 3: Templates + dashboard rewrite

### Przegląd

Dodaj `habit_form.html` (used by create+update), `habit_confirm_archive.html`, i przepisz `dashboard.html` żeby pokazywał empty-state lub listę habits. Po tej fazie pełny happy path UX działa lokalnie.

### Wymagane zmiany

#### 1. Habit form template

**Plik**: `templates/habits/habit_form.html` (nowy — z nowym katalogiem `habits/`)

**Cel**: Render formularza dla obu CreateView i UpdateView. Tailwind styling spójny z `templates/registration/login.html`. Polskie etykiety.

**Kontrakt**: Extends `base.html`, content block z `<form method="post">` zawierającym `{% csrf_token %}`, manual render pola `name` z błędami (Tailwind klasy jak w login.html), submit button "Zapisz". Title block: `{% if form.instance.pk %}Edytuj nawyk{% else %}Dodaj nawyk{% endif %}`. Link "Anuluj" z `{% url 'accounts:dashboard' %}`.

#### 2. Archive confirm template

**Plik**: `templates/habits/habit_confirm_archive.html` (nowy)

**Cel**: Confirm page dla archive action. Wyjaśnia że historia zostanie zachowana.

**Kontrakt**: Extends `base.html`, content block z `<h1>Archiwizuj nawyk</h1>`, paragraph `Czy na pewno chcesz zarchiwizować "<strong>{{ habit.name }}</strong>"? Historia wykonań zostanie zachowana, ale nawyk zniknie z listy aktywnych.`, `<form method="post">` z `{% csrf_token %}` + submit button "Archiwizuj" (czerwonawy/ostrzegawczy Tailwind styling) + link "Anuluj" do `{% url 'accounts:dashboard' %}`.

#### 3. Dashboard rewrite (empty-state + populated branching)

**Plik**: `templates/accounts/dashboard.html` (modyfikacja)

**Cel**: Pokazać listę aktywnych nawyków lub empty-state CTA. Usunąć stary placeholder `href="#"`.

**Kontrakt**: Content block z `<h1>Witaj, {{ user.email }}</h1>`, następnie `{% if habits %}`:
- Lista `<ul>` z `{% for habit in habits %}` → `<li>` z `{{ habit.name }}` + link "Edytuj" (`{% url 'habits:edit' habit.pk %}`) + link "Archiwizuj" (`{% url 'habits:archive' habit.pk %}`).
- Pod listą: `<a href="{% url 'habits:add' %}" class="...">Dodaj kolejny</a>`.

`{% else %}`:
- Paragraph "Nie masz jeszcze żadnych nawyków" (zachowany z S-01).
- `<a href="{% url 'habits:add' %}" class="...">Dodaj swój pierwszy nawyk</a>` (zastępuje `href="#"`).

`{% endif %}`. Usunąć komentarz HTML `<!-- TODO: S-02 — point href to {% url 'habits:add' %} -->`.

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py check` przechodzi bez "template does not exist" warnings
- `uv run python manage.py collectstatic --no-input --dry-run` przechodzi

#### Weryfikacja ręczna

- `/habits/add/` (zalogowany) → render formularza z Tailwind styling, polskim labelem "Nazwa", submit "Zapisz"
- Submit z pustym name → walidacja błąd (Django pl translation), 200
- Submit z duplicate name (same user) → walidacja błąd, 200
- Submit z prawidłową nazwą → redirect `/`, dashboard pokazuje nowy nawyk
- Dashboard pusty (świeży użytkownik) → empty-state CTA z prawidłowym linkiem
- Dashboard z 1+ nawykami → lista z "Edytuj" / "Archiwizuj" + "Dodaj kolejny"
- Klik "Edytuj" → `/habits/<id>/edit/`, formularz pre-filled, zmiana nazwy + zapis → dashboard z nową nazwą
- Klik "Archiwizuj" → confirm page; submit → redirect `/`, nawyk zniknął z dashboardu
- Direct URL `/habits/<istniejący>/archive/` jako NIE-owner → 404

**Uwaga implementacyjna**: Po pełnej manual weryfikacji happy path lokalnie, zatrzymaj się na confirm przed Phase 4.

---

## Faza 4: Tests + per-user isolation matrix + deployment verify

### Przegląd

Napisz `habits/tests.py` z pełnym cross-user matrix, update `accounts/tests.py:DashboardViewTests` o habit context, re-verify `check --deploy` zwraca dokładnie 2 warningi (W005, W021 — opt-in HSTS preload). Po tej fazie S-02 jest produkcyjnie zielony.

### Wymagane zmiany

#### 1. Habits tests

**Plik**: `habits/tests.py`

**Cel**: Pokryć FR-005/006/007 happy path + pełny cross-user matrix per CLAUDE.md hard rule. Klasy testowe muszą mieć `@override_settings(SECURE_SSL_REDIRECT=False)` (retro F1 follow-up).

**Kontrakt**: Klasy:
- `HabitCreateViewTests(TestCase)`:
  - `test_create_creates_habit_for_logged_in_user`
  - `test_create_strips_whitespace_from_name`
  - `test_create_rejects_duplicate_name_for_same_user`
  - `test_create_allows_duplicate_name_across_different_users`
  - `test_create_requires_login` (302 do login)
- `HabitUpdateViewTests(TestCase)`:
  - `test_update_changes_name_for_own_habit`
  - `test_update_rejects_other_users_habit_with_404` (GET + POST — cross-user matrix)
  - `test_update_requires_login`
- `HabitArchiveViewTests(TestCase)`:
  - `test_archive_get_shows_confirm_page_for_own_habit`
  - `test_archive_post_sets_archived_true_and_redirects`
  - `test_archive_rejects_other_users_habit_with_404` (GET + POST)
  - `test_archive_requires_login`
- `HabitManagerTests(TestCase)`:
  - `test_active_returns_only_users_unarchived_habits` (queryset-level isolation, niezależnie od HTTP)

Każda klasa testowa: `@override_settings(SECURE_SSL_REDIRECT=False)` (per retro F1 follow-up — bez tego SECURE_SSL_REDIRECT=True w prod-mode tests zwraca 301).

#### 2. Update accounts/tests.py DashboardViewTests

**Plik**: `accounts/tests.py`

**Cel**: Dashboard nie tylko wymaga loginu, ale też pokazuje user's habits w context.

**Kontrakt**: Dodać do `DashboardViewTests` (`accounts/tests.py:63`) metody:
- `test_dashboard_shows_users_active_habits` — utwórz habit dla user A, zaloguj się jako A, GET `/`, sprawdź `response.context['habits']` zawiera ten habit, nie zawiera archived ani cudzych
- `test_dashboard_does_not_show_other_users_habits` — utwórz habit dla user A i user B, zaloguj się jako B, sprawdź że context['habits'] nie zawiera nawyku A

#### 3. Commit + push

**Plik**: (nie plik — git operation)

**Cel**: Push triggeruje Render auto-deploy z migracją `habits.0001_initial` na Supabase Postgres.

**Kontrakt**: Zacommitować po fazach lub jednym commit'em "feat(manage-habits): habits CRUD with per-user isolation". `git add habits/ habit_coach_ai/{settings,urls}.py accounts/{views,tests}.py templates/`. Push do `origin/main`. Render auto-deploys.

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py test habits` — wszystkie testy zielone (oczekiwane ~13 metod)
- `uv run python manage.py test accounts` — wszystkie testy zielone (6 oryginalnych z S-01 + 2 nowe = 8 metod)
- `uv run python manage.py test` (oba app razem) — green
- `uv run python manage.py check --deploy` (z `DEBUG=False`, `DJANGO_SECRET_KEY` set) — dokładnie 2 warningi (W005 SECURE_HSTS_INCLUDE_SUBDOMAINS, W021 SECURE_HSTS_PRELOAD) — zgodnie z retro lekcją "success-criteria sign-off must actually read the command output"
- Render deploy log: `Applying habits.0001_initial... OK` w preDeployCommand fazie + service `live`

#### Weryfikacja ręczna

- `https://habit-coach-ai.onrender.com/` zalogowany → dashboard z empty-state lub listą
- Production: dodanie nawyku → dashboard pokazuje
- Production: edycja nazwy → dashboard pokazuje nową
- Production: archiwizacja → confirm page → POST → dashboard bez tego nawyku
- Production: próba `/habits/<cudzy_id>/edit/` (zalogowany jako inny user) → 404
- Supabase Tables → `habits_habit` istnieje z odpowiednim rekordem (lub kilku)
- Render Logs — brak 5xx errors po smoke scenariuszu

**Uwaga implementacyjna**: Po zielonym prod deploy + smoke teście, S-02 gotowy do `/10x-impl-review manage-habits` przed `/10x-archive`.

---

## Strategia testowania

### Testy jednostkowe

- ~13 testów w `habits/tests.py` plus 2 nowe w `accounts/tests.py` — pokrywają FR-005/006/007 happy path, walidację (duplikaty, whitespace, pusty name), per-user isolation matrix (GET + POST + queryset-level).
- Każda klasa testowa z `@override_settings(SECURE_SSL_REDIRECT=False)`.
- Brak fixture'ów per test (każdy tworzy User + Habit w `setUp` lub inline).

### Testy integracyjne

- Pełny flow add → edit → archive pokryty przez kombinację testów HTTP w `habits/tests.py` (każdy z `self.client.post(...)` + assertion na DB state).
- Production smoke test (manual) potwierdza end-to-end z migracją na Supabase.

### Kroki testowania ręcznego

1. Lokalnie: `uv run python manage.py runserver` → rejestracja → dashboard z empty-state → kliknij "Dodaj swój pierwszy nawyk" → wpisz "Czytanie" → submit → dashboard z "Czytanie" + "Dodaj kolejny".
2. Lokalnie: kliknij "Edytuj" przy "Czytanie" → zmień na "Czytanie książek" → zapisz → dashboard z nową nazwą.
3. Lokalnie: kliknij "Archiwizuj" → confirm page → submit → dashboard pusty (empty-state znowu).
4. Lokalnie: spróbuj dodać "Czytanie książek" znowu → walidacja błąd duplikatu (polski komunikat).
5. Lokalnie: utwórz drugiego usera w admin → zaloguj jako on → próbuj `/habits/<id_pierwszego_usera>/edit/` → 404.
6. Production: powtórz kroki 1-3 na `https://habit-coach-ai.onrender.com/`.
7. Production: sprawdź Supabase Tables → `habits_habit` ma wpis.

## Uwagi dotyczące wydajności

Wszystkie endpointy są server-rendered HTML, max 2 zapytania DB per request (User session lookup + Habit queryset). Brak N+1 (Habit nie ma related fields w S-02 — HabitExecution dochodzi w S-03 i wymaga `select_related` w S-04 AI prompt assembly, nie tutaj). NFR PRD <200ms dotyczy FR-008 (logging) — auth + habits CRUD nie mają twardych budżetów.

## Uwagi dotyczące migracji

`habits.0001_initial` zależy od `accounts.User` (już istnieje w lokalnym SQLite i w Supabase Postgres). Brak istniejących danych do migracji (fresh model). Forward-only, brak destrukcyjnych operacji. Jeśli kiedyś trzeba będzie dodać pole — dodatkowy migration step (nie planujemy w tym slice).

## Referencje

- Powiązane wycinki: `context/foundation/roadmap.md` (S-02)
- Twarde reguły: `CLAUDE.md` (per-user isolation), `AGENTS.md` (Hard rules)
- PRD: `context/foundation/prd.md` (US-01, FR-005, FR-006, FR-007)
- Wzorzec per-app: `context/archive/2026-06-04-register-and-login/plan.md` + `accounts/` w bazie kodu
- Lekcja retro: `context/foundation/lessons.md` (success-criteria sign-off must read output)
- Django docs: CreateView/UpdateView/View — `https://docs.djangoproject.com/en/6.0/ref/class-based-views/generic-editing/`, UniqueConstraint — `https://docs.djangoproject.com/en/6.0/ref/models/constraints/`

## Progress

> Konwencja: `- [ ]` oczekujące, `- [x]` wykonane. Dodaj ` — <commit sha>`, gdy krok zostanie zrealizowany. Nie zmieniaj nazw tytułów kroków. Zobacz `references/progress-format.md`.

### Faza 1: Habits app + Habit model + UserManager + admin + migration

#### Automatyczne

- [x] 1.1 `manage.py check` przechodzi bez warnings — 519e948
- [x] 1.2 `manage.py makemigrations --check habits` zwraca "No changes detected" po wygenerowaniu migracji — 519e948
- [x] 1.3 `manage.py migrate` przechodzi — 519e948
- [x] 1.4 Tabela `habits_habit` istnieje w db.sqlite3 — 519e948

#### Ręczne

- [x] 1.5 `manage.py runserver` startuje bez błędu — 519e948
- [x] 1.6 `/admin/` — sekcja "Habits" widoczna z list_display + filter — 519e948
- [x] 1.7 Próba dodania duplikatu nazwy przez admin → UniqueConstraint blokuje — 519e948

### Faza 2: Views + URL wiring + DashboardView update

#### Automatyczne

- [x] 2.1 `manage.py check` przechodzi — 229b22a
- [x] 2.2 URL resolver pasuje endpointy: `/habits/add/`, `/habits/<int>/edit/`, `/habits/<int>/archive/` — 229b22a
- [x] 2.3 Brak ImportError przy `from habits.models import Habit` w accounts/views.py — 229b22a

#### Ręczne

- [x] 2.4 `/habits/add/` (zalogowany) → 200 lub TemplateDoesNotExist (OK przed Phase 3) — 229b22a
- [x] 2.5 `/habits/<id>/edit/` jako NIE-owner → 404 — 229b22a
- [x] 2.6 `/habits/<id>/archive/` jako NIE-owner → 404 (GET i POST) — 229b22a

### Faza 3: Templates + dashboard rewrite

#### Automatyczne

- [x] 3.1 `manage.py check` przechodzi bez "template does not exist" — 5b88985
- [x] 3.2 `manage.py collectstatic --no-input --dry-run` przechodzi — 5b88985

#### Ręczne

- [x] 3.3 `/habits/add/` — formularz z Tailwind styling, polski label — 5b88985
- [x] 3.4 Submit pusty name → walidacja błąd — 5b88985
- [x] 3.5 Submit duplicate name → walidacja błąd (fix: 500→walidacja, patrz commit body) — 5b88985
- [x] 3.6 Submit prawidłowy → redirect `/`, nawyk widoczny na dashbordzie — 5b88985
- [x] 3.7 Dashboard pusty (świeży user) → empty-state CTA z linkiem do `/habits/add/` — 5b88985
- [x] 3.8 Dashboard z nawykami → lista z "Edytuj" / "Archiwizuj" + "Dodaj kolejny" — 5b88985
- [x] 3.9 Klik "Edytuj" → form pre-filled → zmień nazwę → dashboard z nową — 5b88985
- [x] 3.10 Klik "Archiwizuj" → confirm page → POST → dashboard bez tego nawyku — 5b88985

### Faza 4: Tests + per-user isolation matrix + deployment verify

#### Automatyczne

- [x] 4.1 `manage.py test habits` — wszystkie testy zielone (13 metod) — 8889ee8
- [x] 4.2 `manage.py test accounts` — wszystkie testy zielone (8 metod) — 8889ee8
- [x] 4.3 `manage.py test` (oba app razem) — green (21) — 8889ee8
- [x] 4.4 `manage.py check --deploy` (DEBUG=False) — dokładnie 2 warningi (W005, W021), nic więcej — 8889ee8
- [x] 4.5 Service live (trasy `/habits/*` przeszły 404→302 o 12:25:18); migracja `habits.0001_initial` potwierdzona funkcjonalnie — dashboard zalogowanego zwraca 200 wykonując `Habit.objects.active()` (tabela istnieje). Log Render nie odczytany wprost (brak Render MCP) — 8889ee8

#### Ręczne

- [x] 4.6 Production: rejestracja nowego konta → dashboard empty-state (curl smoke) — 8889ee8
- [x] 4.7 Production: dodanie nawyku → dashboard pokazuje ('Czytanie') — 8889ee8
- [x] 4.8 Production: edycja → dashboard pokazuje nową nazwę ('Bieganie', POST 302) — 8889ee8
- [x] 4.9 Production: archiwizacja → POST 302 → dashboard bez nawyku (z powrotem empty-state) — 8889ee8
- [x] 4.10 Production: user B → `/habits/<id_A>/edit/` i `/archive/` → 404, A nadal widzi swój — 8889ee8
- [x] 4.11 `habits_habit` ma wpisy — potwierdzone funkcjonalnie (rekordy zapisane i odczytane przez curl smoke); Supabase UI nie otwierany — 8889ee8
- [x] 4.12 Brak 5xx zaobserwowanych w ~20 żądaniach smoke (wszystkie 200/302/404); Render Logs nie tailowane wprost — 8889ee8

> Uwaga: prod-smoke utworzył jednorazowe konta testowe (`smoke+*`, `smoke2+*`, `ucA+*`, `ucB+*@example.com`) i kilka nawyków w Supabase. Do posprzątania przez Django admin / SQL przy okazji.
