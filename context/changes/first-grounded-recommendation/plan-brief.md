# First grounded recommendation — plan brief

> Pełny plan: `context/changes/first-grounded-recommendation/plan.md`

## Co i dlaczego

Gwiazda przewodnia MVP (S-04). Daje zalogowanemu użytkownikowi rekomendację AI **na żądanie** (FR-011), która cytuje jego konkretne nawyki i wzorce z 30-dniowej historii — to różnicuje produkt od generycznych porad i broni głównej hipotezy. Ostatnia rekomendacja jest widoczna po powrocie (FR-012).

## Punkt wyjścia

Po S-03 istnieje pełna pętla danych: nawyki (S-02) + logowanie wykonań i 30-dniowa historia (S-03), z per-user isolation i HTMX. Brak jakiejkolwiek integracji AI, brak klienta LLM, brak konfiguracji OpenRouter. Stos server-rendered + HTMX + Tailwind.

## Pożądany stan końcowy

Na dashboardzie (gdy jest ≥1 nawyk i ≥1 wykonanie) przycisk „Wygeneruj rekomendację" → spinner HTMX → w <10s karta z tekstem AI odnoszącym się do nazw nawyków i policzonych wzorców (streak, % ukończenia, najsłabszy dzień, ostatnia przerwa). Ostatnia rekomendacja widoczna po powrocie. Bez danych — empty-state z instrukcją. Błąd API → przyjazny komunikat, bez zapisu.

## Kluczowe podjęte decyzje

| Decyzja | Wybór | Dlaczego | Źródło |
|---|---|---|---|
| Pomiar kryterium 75% (Q2) | Hybryda, obserwacyjnie (log token-check, bez bramki) | Mierzalne od razu + ground-truth z ręcznego; nie ryzykuje NFR/kosztu | PRD Q2 |
| Klient LLM | openai SDK → base_url OpenRouter | OpenRouter OpenAI-compatible; dojrzałe SDK, timeout/streaming wbudowane | Plan |
| Model | `anthropic/claude-haiku-4-5` przez env | Mocny grounding, szybki (<10s), tani, konfigurowalny bez deployu | Roadmap+Plan |
| Latencja/UX | Synchronicznie + wskaźnik HTMX + twardy timeout ~9s | Haiku <10s; „progres co 2s" (tylko gdy >10s) nie wchodzi; zero SSE | Plan |
| Miejsce UI | Sekcja na dashboardzie | Kontekstowo (PRD), FR-012 trywialne, reuse dashboardu | Plan |
| Dane promptu | Surowa tabela 30 dni + sygnały (streak/%/weak-day/break) | To „konkretne elementy" które kryterium 75% nagradza | Plan |
| Persystencja | Dopisuj wszystkie wiersze, pokaż ostatnią | FR-012 + dane do metryki Q2 | Plan |
| Próg generowania | ≥1 aktywny nawyk + ≥1 wykonanie | Minimalny sensowny grounding; nie myli z progiem FR-013 (S-06) | Plan |
| Błąd API | Friendly error, bez zapisu, retry ręczny | Brak śmieci w DB, chroni NFR/koszt | Plan |

## Zakres

**W zakresie:** `Recommendation` model + migracja; `openai` dep + config OpenRouter z env; moduł `recommendations.py` (kontekst+sygnały, prompt, wywołanie, token-check); `RecommendationGenerateView` + URL; sekcja rekomendacji na dashboardzie (HTMX); guard progu danych; obsługa błędów; metryka `grounded`; testy z mockiem LLM; deploy.

**Poza zakresem:** FR-013 (proaktywna — S-06); historia rekomendacji w UI; streaming/SSE; background jobs; bramkowanie/regeneracja gdy generyczne; auto-retry; eval wielu modeli; markdown z modelu.

## Architektura / Podejście

Czysty podział logika/UI. `habits/recommendations.py`: `build_history_context(user)` (tylko dane usera → 30-dniowa siatka + sygnały), `build_messages`, `generate_recommendation(user)` (openai SDK → OpenRouter, timeout, błąd propaguje), `is_grounded(text, user)` (token-check), `can_generate(user)`. `RecommendationGenerateView.post` guarduje, woła service, persystuje z `grounded`, zwraca partial (HTMX) lub błąd. Dashboard pokazuje ostatnią + przycisk. Izolacja: prompt budowany wyłącznie z `request.user`.

## Fazy w skrócie

| Faza | Co dostarcza | Kluczowe ryzyko |
|---|---|---|
| 1. Model + deps + config | `Recommendation` + migracja `0003`, openai dep, OpenRouter env | Klucz pusty lokalnie (default), nie wywalać `check` |
| 2. Logika AI (service) | Kontekst+sygnały, prompt, wywołanie, token-check | Jakość groundingu; izolacja w prompcie; timeout |
| 3. View + dashboard (HTMX) | Generate view, sekcja, guard, błędy | NFR <10s; stany guard/error; brak wycieku |
| 4. Testy (mock) + deploy | Matryca z mockiem LLM, check --deploy, prod smoke | Klucz w Render env; realne wywołanie w smoke; brak sieci w testach |

**Wymagania wstępne:** S-03 (historia do groundingu) ✓; `OPENROUTER_API_KEY` w Render env (przed prod smoke).
**Szacowany nakład pracy:** ~4-5 sesji w 4 fazach (pierwsza integracja zewnętrznego API).

## Otwarte ryzyka i założenia

- Jakość groundingu Haiku do progu 75% — do walidacji na próbkach (iteracja promptu w S-06); token-check obserwacyjny da pierwszy sygnał.
- Synchroniczne wywołanie blokuje worker — OK dla małej skali MVP; monitoruj CPU na Render Starter.
- Koszt OpenRouter — budget alert $20/mo (infra); jeden model przez env, NIE gpt-4.

## Kryteria sukcesu (podsumowanie)

- Jedno kliknięcie → w <10s rekomendacja cytująca konkretne nawyki/wzorce usera; ostatnia widoczna po powrocie.
- Prompt zawiera wyłącznie dane bieżącego usera (test cross-user isolation zielony).
- `grounded` logowany/zapisywany na każdej rekomendacji jako metryka Primary criterion (Q2).
