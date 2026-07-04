# Najdłuższy streak — plan implementacji

## Przegląd

Mała, post-MVP zmiana do przećwiczenia TDD (M3L2). Dodaje **najdłuższą serię kolejnych dni** (longest
streak) jako metrykę per-nawyk w oknie 30 dni. Trzy kroki, wszystkie test-first: (1) czysta funkcja
`longest_streak`, (2) wpięcie w `build_history_context` (nowe pole `longest_streak`), (3) wystawienie
w promptcie AI (`build_messages`) jako dodatkowy ugruntowany sygnał. Zero zmian w modelu/migracji.

## Analiza stanu obecnego

- `build_history_context(user)` (`habits/recommendations.py:35`) liczy już `current_streak` pętlą wstecz
  od dziś po zbiorze `done` = `(habit_pk, date)`. Brakuje **najdłuższej** serii w całym oknie.
- `build_messages(context)` (`habits/recommendations.py`) buduje linie promptu z sygnałów per-nawyk.
- Testy: `habits/tests.py`, wzorce `@override_settings(SECURE_SSL_REDIRECT=False)`, `RecommendationContextTests`.
- Brak jakiejkolwiek implementacji „longest streak" — czysta funkcja do napisania test-first.

## Pożądany stan końcowy

- Czysta funkcja `longest_streak(dates)` → int: najdłuższa seria kolejnych dni w podanym zbiorze dat
  (0 dla pustego, poprawna dla luk, niezależna od kolejności).
- `build_history_context` zwraca per-nawyk `longest_streak`.
- `build_messages` dołącza „najdłuższa seria: N dni" do linii nawyku (dodatkowy sygnał AI).
- ~5 testów zielonych, całość zielona. Zero zmian w modelu.

## Czego NIE robimy

- Żadnego nowego UI/strony (analytics zarchiwizowane; to metryka + sygnał AI).
- Żadnych zmian modelu/migracji ani nowych zależności.

## Podejście do implementacji

Jedna faza, w pełni test-first: funkcja → integracja w kontekście → prompt. Każdy krok RED→GREEN→REFACTOR.

## Faza 1: longest_streak — funkcja, kontekst, prompt (TDD)

### Wymagane zmiany

- `habits/recommendations.py`: dodaj czystą funkcję `longest_streak(dates)`; użyj jej w `build_history_context`
  (pole `longest_streak` per-nawyk, liczone ze zbioru dat wykonań danego nawyku w oknie); dołącz sygnał
  do linii promptu w `build_messages`.

### Kryteria sukcesu

#### Weryfikacja automatyczna

- `uv run python manage.py test habits` — zielone (+~5 nowych)
- `uv run python manage.py test` — green
- `uv run python manage.py check` przechodzi

#### Weryfikacja ręczna

- (opcjonalnie) rekomendacja AI na prodzie cytuje najdłuższą serię, gdy istnieje.

### Testy

**Plik**: `habits/tests.py`

- `LongestStreakTests`: pusty zbiór → 0; jeden dzień → 1; 3 kolejne → 3; luka rozbija serię (bierze dłuższą);
  kolejność wejścia bez znaczenia.
- `RecommendationContextTests` (lub nowa): `build_history_context` zwraca poprawny `longest_streak` per-nawyk.
- prompt: `build_messages` zawiera „najdłuższa seria" gdy > 1.

## Strategia testowania

Czysta logika + integracja kontekstu/promptu; brak sieci/LLM (funkcje lokalne). ~5 testów.

## Uwagi dotyczące migracji

Brak.

## Referencje

- `build_history_context`, `build_messages` (`habits/recommendations.py`)
- Ćwiczenie M3L2 (`/10x-tdd`), lekcje `context/foundation/lessons.md`

## Progress

> `- [ ]` oczekujące, `- [x]` wykonane. Dodaj ` — <sha>` na końcu fazy.

### Faza 1: longest_streak — funkcja, kontekst, prompt (TDD)

#### Automatyczne

- [x] 1.1 Czysta funkcja `longest_streak(dates)` (RED→GREEN→REFACTOR; testy: pusty/1/kolejne/luka/kolejność) — 17e0840
- [x] 1.2 `build_history_context` zwraca per-nawyk `longest_streak` (test integracyjny) — 17e0840
- [x] 1.3 `build_messages` dołącza sygnał „najdłuższa seria" (test promptu) — 17e0840
- [x] 1.4 `manage.py test` (całość) — green (87) + `check` — 17e0840

#### Ręczne

- [ ] 1.5 (opcjonalnie) prod: rekomendacja cytuje najdłuższą serię
