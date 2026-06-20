# Log execution and history — plan brief

> Pełny plan: `context/changes/log-execution-and-history/plan.md`

## Co i dlaczego

Trzeci wycinek MVP (S-03). Pozwala zalogowanemu użytkownikowi logować wykonania nawyków jednym kliknięciem („wykonane dziś", toggle) i przeglądać 30-dniową historię jako siatkę. To wypełnia US-01 między „mam nawyki" (S-02) a „AI czyta moją historię" (S-04) — produkuje dane wykonań, które są surowcem dla rekomendacji.

## Punkt wyjścia

Po S-02 istnieje `habits/` app z modelem `Habit`, dashboardem listującym aktywne nawyki (Edytuj/Archiwizuj) i wzorcem per-user isolation. Brak jakiegokolwiek logowania wykonań, brak historii, brak JS/HTMX. Stos czysto server-rendered (Django + Tailwind CDN).

## Pożądany stan końcowy

Przy każdym nawyku na dashboardzie jest przycisk toggle, który jednym kliknięciem loguje/cofa wykonanie bieżącego dnia bez przeładowania strony (<200ms). Osobna strona `/habits/history/` pokazuje read-only siatkę: aktywne nawyki × ostatnie 30 dni, z oznaczeniem wykonane/niewykonane. Backdating jest niemożliwy — można dotknąć tylko dzisiejszego dnia.

## Kluczowe podjęte decyzje

| Decyzja | Wybór | Dlaczego | Źródło |
|---|---|---|---|
| Interaktywność toggle (<200ms) | HTMX przez CDN | Bez reloadu, pasuje do „CDN bez build" jak Tailwind; zero nowej zależności Pythona | Plan |
| „Dziś" / strefa czasu | `TIME_ZONE=Europe/Warsaw` + `localdate()` | Poprawna granica doby dla użytkowników PL; jedno ustawienie | Plan |
| Układ historii | Wspólna siatka (aktywne × 30 dni) | Zgodne z roadmap/PRD „siatka 30 dni × nawyk"; wzorzec na pierwszy rzut oka | Plan |
| Miejsce toggle | Na istniejącym dashboardzie | PRD AC: dashboard listuje nawyki z przyciskiem done; reuse S-02 | Plan |
| Tryb historii | Read-only | Toggle tylko na dashboardzie; jedno źródło akcji, mniej endpointów | Plan |
| Zakres historii | Tylko aktywne nawyki | Spójne z S-02 (archiwum ukryte); dane archiwalnych zostają w DB dla AI | Plan |
| Brak backdatingu | Z konstrukcji (brak endpointu na datę) | FR-009 niewzruszalny — nie ma czego obejść; toggle zawsze na `localdate()` | Plan |
| Testy | Pełna matryca (~14) | Lustro rygoru S-02; pokrywa isolation + regułę domeny | Plan |

## Zakres

**W zakresie:** Model `HabitExecution(habit, date, created_at)` + unique `(habit, date)`; toggle endpoint (create/undo dziś); HTMX + partial przycisku; done-today na dashboardzie; read-only siatka 30 dni; `TIME_ZONE=Europe/Warsaw`; pełna matryca testów; deploy.

**Poza zakresem:** Backdating/undo wstecz; klikalna historia; historia zarchiwizowanych w UI; streaki/statystyki; AI (S-04); powiadomienia; per-user timezone; non-JS UI ponad redirect-fallback.

## Architektura / Podejście

Obecność rekordu `(habit, date)` = „wykonane"; undo = `DELETE`. Jedyny endpoint mutujący (`HabitToggleView.post`) operuje na `timezone.localdate()` z `get_object_or_404(Habit, pk, user=request.user, archived=False)` — isolation + brak backdatingu z konstrukcji. HTMX (`hx-post`, `hx-swap="outerHTML"`, CSRF przez `hx-headers` na body) podmienia partial przycisku in-place; nagłówek `HX-Request` rozróżnia odpowiedź partial (z JS) od redirect (bez JS). Dashboard i historia liczą stan setami z 1-2 zapytań (bez N+1).

## Fazy w skrócie

| Faza | Co dostarcza | Kluczowe ryzyko |
|---|---|---|
| 1. Model + TIME_ZONE | `HabitExecution` + manager + admin + migracja `0002`; strefa Warsaw | Poprawność „dziś" zależna od USE_TZ + strefy |
| 2. Toggle + HTMX | Endpoint toggle, partial, HTMX w base, done-today na dashboardzie | CSRF dla HTMX; <200ms; isolation 404 |
| 3. Historia 30 dni | Read-only siatka, blok szerokości w base, link | Szerokość kontenera (max-w-md za wąski); N+1 |
| 4. Testy + deploy | Pełna matryca, `check --deploy`, prod smoke | Migracja `0002` na Supabase; asercje daty wg localdate |

**Wymagania wstępne:** S-02 (zarchiwizowany, `habits/` app + dashboard).
**Szacowany nakład pracy:** ~3-4 sesje w 4 fazach (zbliżony do S-02 + lekki front HTMX).

## Otwarte ryzyka i założenia

- HTMX z CDN (`unpkg`) — założenie dostępności CDN w prod; pin major `@2`. Fallback redirect działa bez JS, ale nie bez sieci CDN dla pełnego UX.
- `TIME_ZONE=Europe/Warsaw` zakłada single-region; użytkownik spoza PL zobaczy granicę doby wg Warszawy (świadomy tradeoff MVP).

## Kryteria sukcesu (podsumowanie)

- Jedno kliknięcie loguje/cofa wykonanie bieżącego dnia z natychmiastowym potwierdzeniem bez reloadu (<200ms).
- Historia 30 dni pokazuje czytelny wzorzec wykonane/niewykonane dla aktywnych nawyków; backdating niemożliwy.
- Dane jednego użytkownika nigdy nie widoczne/mutowalne przez innego (pełna matryca testów isolation zielona).
