---
project: HabitCoach AI
version: 1
status: active
created: 2026-06-28
prd_version: 1
test_runner: "Django test runner (uv run python manage.py test)"
total_tests: 72
---

# Plan testów: HabitCoach AI

Ten dokument definiuje **konkretne ryzyka** produktowo-bezpieczeństwowe MVP i mapuje każde z nich
na istniejące testy automatyczne, które je adresują. Testy to brama jakości dla guardraili z PRD
(`context/foundation/prd.md`), nie pełne pokrycie liniowe.

- **Runner:** `uv run python manage.py test` (domyślny runner Django; pytest nie jest skonfigurowany).
- **Środowisko:** klasy izolacji sieciowej używają `@override_settings(SECURE_SSL_REDIRECT=False)`;
  wywołania LLM są mockowane (`unittest.mock`) — testy nie wychodzą do sieci.
- **Liczba testów:** 72 (`accounts` 22 + `habits` 50).

## Macierz ryzyk → testy

### R1 — Wyciek danych między użytkownikami (load-bearing) · krytyczne

**Ryzyko:** nawyki, wykonania lub rekomendacje jednego użytkownika stają się widoczne dla innego
użytkownika lub gościa. To główny invariant bezpieczeństwa MVP (PRD § Success Criteria — Guardrails);
naruszenie = dyskwalifikujący błąd.

**Mitygacja:** każdy widok/queryset filtruje po `request.user`; dostęp do cudzego zasobu zwraca **404**
(nie 403 — nie ujawniamy istnienia). Mapowane testy:

- `accounts/tests.py::DashboardViewTests::test_dashboard_does_not_show_other_users_habits`
- `habits/tests.py::HabitUpdateViewTests::test_update_rejects_other_users_habit_with_404`
- `habits/tests.py::HabitArchiveViewTests::test_archive_rejects_other_users_habit_with_404`
- `habits/tests.py::HabitToggleViewTests::test_toggle_rejects_other_users_habit_with_404`
- `habits/tests.py::HabitHistoryViewTests::test_history_excludes_other_users_habits`
- `habits/tests.py::HabitExecutionManagerTests::test_done_habit_ids_for_returns_only_users_executions_on_date`
- `habits/tests.py::HabitExecutionManagerTests::test_history_for_excludes_archived_and_other_users_and_old`
- `habits/tests.py::RecommendationContextTests::test_context_isolation_excludes_other_users`
- `habits/tests.py::RecommendationGenerateViewTests::test_generate_uses_only_request_user_data`
- `habits/tests.py::RecommendationModelTests::test_latest_for_returns_users_most_recent_not_others`
- `habits/tests.py::HabitManagerTests::test_active_returns_only_users_unarchived_habits`
- `habits/tests.py::AutoRecommendationDueTests::test_threshold_is_per_user`

### R2 — Rekomendacja AI generyczna zamiast ugruntowanej · wysokie

**Ryzyko:** rekomendacja AI nie odwołuje się do realnych danych użytkownika („pij więcej wody"),
łamiąc główne kryterium sukcesu PRD (≥ 75 % rekomendacji data-specific; FR-011/FR-013).

**Mitygacja:** kontekst budowany wyłącznie z aktywnych nawyków i historii danego użytkownika; flaga
`grounded` weryfikuje obecność konkretów. Mapowane testy:

- `habits/tests.py::IsGroundedTests::test_grounded_true_when_habit_name_present`
- `habits/tests.py::IsGroundedTests::test_grounded_false_for_generic_text`
- `habits/tests.py::RecommendationGenerateViewTests::test_generated_recommendation_grounded_flag_set`
- `habits/tests.py::RecommendationGenerateViewTests::test_generate_uses_only_request_user_data`
- `habits/tests.py::RecommendationContextTests::test_context_signals_and_active_only`
- `habits/tests.py::RecommendationContextTests::test_context_weakest_weekday_none_when_fully_complete`

### R3 — Logowanie wsteczne / integralność streaków · wysokie

**Ryzyko:** użytkownik oznacza wykonanie dla innego dnia niż dziś albo tworzy duplikat wpisu,
zaburzając streaki, na których opiera się AI (FR-009 — reguła domenowa, nie kosmetyka UI).

**Mitygacja:** toggle tworzy/usuwa wykonanie tylko dla bieżącego dnia; unikalność per nawyk-dzień
egzekwowana na poziomie bazy; toggle zarchiwizowanego nawyku → 404. Mapowane testy:

- `habits/tests.py::HabitToggleViewTests::test_toggle_creates_execution_for_today`
- `habits/tests.py::HabitToggleViewTests::test_toggle_twice_removes_execution`
- `habits/tests.py::HabitExecutionModelTests::test_unique_constraint_blocks_duplicate_per_day`
- `habits/tests.py::HabitToggleViewTests::test_toggle_rejects_archived_habit_with_404`

### R4 — Dostęp bez uwierzytelnienia / niebezpieczne wylogowanie · krytyczne

**Ryzyko:** zasób dostępny bez logowania, albo wylogowanie wykonalne przez GET
(`<img>`/prefetch/CSRF), albo enumeracja kont przy resecie hasła.

**Mitygacja:** każdy widok danych wymaga logowania (redirect na login dla anonima); `LogoutView`
jest POST-only (Django 6 → GET = 405); reset hasła nie ujawnia istnienia konta. Mapowane testy:

- `accounts/tests.py::DashboardViewTests::test_dashboard_requires_login`
- `habits/tests.py::HabitCreateViewTests::test_create_requires_login`
- `habits/tests.py::HabitUpdateViewTests::test_update_requires_login`
- `habits/tests.py::HabitArchiveViewTests::test_archive_requires_login`
- `habits/tests.py::HabitToggleViewTests::test_toggle_requires_login`
- `habits/tests.py::HabitHistoryViewTests::test_history_requires_login`
- `habits/tests.py::RecommendationGenerateViewTests::test_generate_requires_login`
- `habits/tests.py::RecommendationAutoViewTests::test_auto_requires_login`
- `accounts/tests.py::LogoutTests::test_logout_post_invalidates_session_and_redirects`
- `accounts/tests.py::LogoutTests::test_logout_get_not_allowed`
- `accounts/tests.py::PasswordResetFlowTests::test_reset_unknown_email_does_not_reveal_and_sends_nothing`
- `accounts/tests.py::PasswordResetFlowTests::test_used_token_link_is_invalid_second_time`

### R5 — Błędne odpalenie proaktywnej rekomendacji (próg) · średnie

**Ryzyko:** proaktywna rekomendacja (FR-013) odpala się przed progiem danych, nie odpala po jego
przekroczeniu, albo spamuje przy każdym wejściu na dashboard.

**Mitygacja:** próg liczony per użytkownik; po wygenerowaniu proaktywnej rekomendacji warunek
„due" gaśnie (jednorazowo); błąd LLM jest cichy i nie zapisuje rekordu. Mapowane testy:

- `habits/tests.py::AutoRecommendationDueTests::test_below_threshold_not_due`
- `habits/tests.py::AutoRecommendationDueTests::test_at_threshold_due`
- `habits/tests.py::AutoRecommendationDueTests::test_not_due_after_proactive_exists`
- `habits/tests.py::AutoRecommendationDueTests::test_threshold_is_per_user`
- `accounts/tests.py::DashboardAutoRecommendationTests::test_should_auto_generate_true_at_threshold`
- `accounts/tests.py::DashboardAutoRecommendationTests::test_should_auto_generate_false_after_proactive`
- `habits/tests.py::RecommendationAutoViewTests::test_auto_generates_proactive_recommendation_when_due`
- `habits/tests.py::RecommendationAutoViewTests::test_auto_noop_when_not_due`
- `habits/tests.py::RecommendationAutoViewTests::test_auto_one_time_after_success`
- `habits/tests.py::RecommendationAutoViewTests::test_auto_silent_on_error`

## Decyzja projektowa: „delete" = archiwizacja (soft-delete)

CRUD na nawykach realizuje usuwanie jako **archiwizację** (`archived=True`), nie twarde skasowanie
rekordu. To **świadoma decyzja domenowa** (PRD § Non-Goals, FR-007): historia wykonań musi przetrwać,
bo AI liczy na niej streaki i wzorce; twarde usunięcie nawyku skasowałoby tę historię kaskadą.
Zarchiwizowany nawyk znika z listy aktywnych, z historii i z kontekstu AI — z perspektywy użytkownika
jest „usunięty". Twarde usunięcie istnieje na poziomie pojedynczego wykonania (odznaczenie toggle →
`execution.delete()`). Pokrycie: `HabitArchiveViewTests`, `HabitManagerTests::test_active_returns_only_users_unarchived_habits`,
`HabitToggleViewTests::test_toggle_twice_removes_execution`.

## Mapowanie na kryteria zgłoszeniowe 10xBuilder

| Kryterium | Pokrycie |
| --- | --- |
| **CRUD** | Create `add/` · Read dashboard + `history/` · Update `<pk>/edit/` · Delete `<pk>/archive/` (soft, decyzja powyżej). Klasy: `HabitCreateViewTests`, `HabitUpdateViewTests`, `HabitArchiveViewTests`, `HabitHistoryViewTests`. |
| **Logika biznesowa** | Ugruntowana rekomendacja AI z historii użytkownika + próg proaktywny (FR-011/013). Ryzyka **R2** i **R5**. |
| **Testy** | Ten dokument + 72 testy adresujące **R1–R5**. |
| **Autentykacja** | Logowanie/rejestracja + izolacja per-user; każdy zasób za loginem. Ryzyka **R1** i **R4**. |

## Jak uruchomić

```bash
uv run python manage.py test            # cały zestaw (72)
uv run python manage.py test accounts   # tylko konta/auth/logout
uv run python manage.py test habits     # nawyki/wykonania/rekomendacje
```

Wymaga `DJANGO_SECRET_KEY` w środowisku (settings czyta surowe `os.environ`); lokalnie patrz `.env`.
