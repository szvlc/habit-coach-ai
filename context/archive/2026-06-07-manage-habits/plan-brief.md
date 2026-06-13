# Manage habits — Krótki plan

> Pełny plan: `context/changes/manage-habits/plan.md`

## Co i dlaczego

Drugi wycinek z roadmapy (S-02 `manage-habits`). Dostarcza FR-005/006/007: zalogowany użytkownik dodaje nawyk, edytuje nazwę, archiwizuje. To pierwszy "domain" app po `accounts/` — tu per-user isolation (CLAUDE.md hard rule) staje się load-bearing i ustanawia wzorzec queryset filtering dla wszystkich kolejnych slice'ów (S-03 logging, S-04 AI rec).

## Punkt wyjścia

`accounts/` (S-01) jest zarchiwizowany i działa jako pełny per-app wzorzec (`models.py` + `forms.py` + `views.py` + `urls.py` + `admin.py` + `tests.py` + `templates/accounts/`). `templates/accounts/dashboard.html:14` ma placeholder CTA `<a href="#">` z komentarzem `<!-- TODO: S-02 — point href to {% url 'habits:add' %} -->` — wpiszemy w nim docelowy link. Brak istniejących project models poza `User`. F-01 (prod deploy) zielony od 2026-06-07.

## Pożądany stan końcowy

Zalogowany użytkownik na `/`: pusty stan → CTA "Dodaj swój pierwszy nawyk"; z nawykami → lista (sortowana `created_at` ASC, archived ukryte) z akcjami "Edytuj"/"Archiwizuj" + "Dodaj kolejny". `/habits/add/`, `/habits/<id>/edit/`, `/habits/<id>/archive/` (GET=confirm, POST=archiwizuj). Cudzy `<id>` zwraca 404 — testowane explicit. Django admin pokazuje `Habit` z `list_display` + filter. ~13 testów habits + 2 nowe accounts zielone, `check --deploy` dokładnie 2 warningi (W005/W021).

## Kluczowe podjęte decyzje

| Decyzja | Wybór | Dlaczego (1 zdanie) | Źródło |
| --- | --- | --- | --- |
| Layout views | Osobne URLs pod `/habits/` (add/edit/archive) | REST-like, czysta separacja od dashboard, każda akcja ma własny test ścieżki | Plan |
| Archive UX | Confirm page (GET pokazuje, POST archiwizuje) | Bezpieczne, CSRF-protected, user rozumie skutek "historia zostanie" | Plan |
| Name walidacja | max 100, strip whitespace, unique per-user (case-sensitive) | Zapobiega duplikatom; AI w S-04 dostaje czyste dane | Plan |
| Per-user isolation test scope | Pełny cross-user matrix (GET+POST na edit+archive) + queryset-level | Pierwsza enforcement hard rule; pattern dla S-03/S-04 | Plan |
| Archived habits w UI | Zupełnie ukryte z dashboardu | PRD FR-007 "nawyk znika z list aktywnych"; recovery przez admin | Plan |
| Dashboard template | Jeden plik z `{% if habits %}` branching | Jeden plik do utrzymania, naturalny Django pattern | Plan |
| Sortowanie aktywnych | `created_at` ASC | Stabilne; "core" nawyki na górze, dobre dla psychiki w S-03 | Plan |
| Django admin | Tak — `@admin.register(Habit)` z list_display + filter | Ops/debug tool gotowy gdy bug reports zaczną przychodzić | Plan |

## Zakres

**W zakresie:**
- Model `Habit(name, user FK, archived, created_at)` + `HabitManager.active(user)` + `UniqueConstraint(user, name)` + `HabitAdmin`
- 3 views: `HabitCreateView`, `HabitUpdateView`, `HabitArchiveView` (każdy `LoginRequiredMixin` + queryset filtering)
- 3 templates: `habit_form.html` (shared create+update), `habit_confirm_archive.html`, dashboard rewrite
- `DashboardView` update — pobiera `Habit.objects.active(user)` do contextu
- Pełny test matrix per-user isolation
- Production deploy + smoke

**Poza zakresem:**
- Logowanie wykonań (FR-008) — S-03
- Hard delete nawyku z historią — PRD §Non-Goals (tylko archive)
- Un-archive z UI — recovery przez admin/SQL
- Częstotliwości inne niż codzienna — PRD §Non-Goals
- AI rekomendacje (FR-011/013) — S-04
- Inline edit na dashbordzie, bulk actions, soft archive z undo, drag-and-drop sorting

## Architektura / Podejście

`habits/` to nowy Django app obok `accounts/`. Cross-app dependency: `accounts.views.DashboardView` importuje `habits.models.Habit` (unidirectional). Trzy views w `habits/views.py` używają Django generic CBVs z load-bearing `get_queryset()` filtrującym po `request.user` — to gwarantuje 404 na cudzych `<id>` przez `SingleObjectMixin.get_object()` zanim widok się załaduje. Templates pod `templates/habits/` (per konwencja ustanowiona w F4 retro). Wzorzec triplet (Model + Manager + Admin) zastosowany od pierwszego commita (w przeciwieństwie do S-01 gdzie UserManager dochodził w Phase 4).

## Fazy w skrócie

| Faza | Co dostarcza | Kluczowe ryzyko |
| --- | --- | --- |
| 1. Foundation | App + Habit model + HabitManager + Admin + migracja | Auto-detect migracji `AUTH_USER_MODEL` (sprawdzony — `accounts.User` aktywny od S-01) |
| 2. Views + URLs | 3 views z load-bearing queryset filter; dashboard update | Cross-app import `accounts → habits` (unidirectional, OK) |
| 3. Templates | habit_form, archive confirm, dashboard rewrite | Empty-state vs populated state branching w jednym templacie |
| 4. Tests + deploy | ~13 testów habits + 2 accounts + check --deploy + prod smoke | `check --deploy` musi mieć dokładnie 2 warningi (lekcja retro F2) |

**Wymagania wstępne:** S-01 zielone (jest), F-01 deploy zielony (jest), Tailwind CDN aktywny (jest przez `templates/base.html:7`).

**Szacowany nakład pracy:** ~1-2 sesje implementacyjne (4 fazy po 30-60 min każda). Mniej niż S-01 bo wzorzec już ustanowiony, ale więcej testów niż S-01 (cross-user matrix).

## Otwarte ryzyka i założenia

- Założenie: `Habit.objects.active(user)` jako helper jest reusable — w S-03 logging viewy też muszą filtrować aktywne nawyki. Jeśli S-03 ujawni, że potrzebuje innego shape querysetu, wymusi refactor.
- Założenie: case-sensitive unique constraint na nazwę jest wystarczający dla MVP. Jeśli user-testing pokaże że "Czytanie" vs "czytanie" jako duplikaty są zaskakujące — zmiana do case-insensitive wymaga functional index na Postgres (citext) lub `LOWER(name)` unique constraint.
- Założenie: empty-state vs populated state w jednym templacie nie urośnie do unmaintenable. Jeśli S-03 doda widok historii (siatka 30 dni × habit) — dashboard staje się złożony i może wymagać partial-extraction (otwarte do decyzji w S-03 planie).

## Kryteria sukcesu (podsumowanie)

- User end-to-end: rejestracja → dodanie nawyku → edycja nazwy → archiwizacja → dashboard zachowuje się zgodnie z PRD FR-005/006/007 i US-01 AC.
- Hard rule enforcement: testy pokrywają cross-user 404 dla GET + POST na edit + archive; queryset manager-level isolation osobno testowane.
- Production deploy: `https://habit-coach-ai.onrender.com/` zielone end-to-end smoke, Supabase `habits_habit` tabela z migracją zastosowaną, `check --deploy` zwraca dokładnie 2 warningi (W005, W021).
