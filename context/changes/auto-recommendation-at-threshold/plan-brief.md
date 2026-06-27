# Auto recommendation at threshold — plan brief

> Pełny plan: `context/changes/auto-recommendation-at-threshold/plan.md`

## Co i dlaczego

Szósty slice (S-06). Dostarcza FR-013: po przekroczeniu progu danych aplikacja **sama** pokazuje pierwszą rekomendację AI — bez klikania „Wygeneruj". To moment, w którym produkt po raz pierwszy pokazuje „coś z tych danych wynika", domykając obietnicę MVP obok on-demand (S-04).

## Punkt wyjścia

Po S-04 istnieje pełna maszyneria rekomendacji (OpenRouter, `generate_recommendation`, model `Recommendation`, sekcja dashboardu, token-check). Brak jakiegokolwiek automatycznego triggera — rekomendacja powstaje wyłącznie po kliknięciu przycisku.

## Pożądany stan końcowy

Użytkownik, który logował wykonania przez ≥7 różnych dni i nie dostał jeszcze proaktywnej rekomendacji, przy wejściu na dashboard widzi „Generuję rekomendację…", po czym pojawia się rekomendacja oznaczona „Automatyczna" — bez żadnej akcji. Dzieje się to raz; potem dashboard działa normalnie (on-demand dalej dostępny).

## Kluczowe podjęte decyzje

| Decyzja | Wybór | Dlaczego | Źródło |
|---|---|---|---|
| Próg (Q1) | ≥7 różnych dni z logowaniem (dowolny nawyk) | Dosłownie „~7 dni logowań" z PRD; proste 1 zapytanie; wystarczający sygnał | PRD Q1 |
| Częstotliwość (Q3) | Jednorazowo (pierwsza po progu) | FR-013 „pierwszą"; default MVP; brak spamu/kosztu | PRD Q3 |
| Trigger | Lazy HTMX (hx-trigger=load) gdy due | Dashboard renderuje się natychmiast, rec dopływa w tle; reuse partiala; request-time, nie cron | Plan |
| Błąd auto-gen | Cicho (log, bez zapisu, retry) | Proaktywne/tło — błąd nie psuje dashboardu; samonaprawialne | Plan |
| Rozróżnienie | Pole `proactive` bool + tag „Automatyczna" | Guard jednorazowości + UX (user wie skąd rec) | Plan |
| Testy | Pełna matryca progu (mock LLM) | Boundary 6/7, jednorazowość, cicha porażka, izolacja | Plan |

## Zakres

**W zakresie:** `Recommendation.proactive` + migracja `0004`; `auto_recommendation_due(user)` (≥7 distinct dni AND brak proaktywnej); `RecommendationAutoView` (lazy POST, guard, generate, persist `proactive=True`, cicha porażka); URL; `DashboardView.should_auto_generate`; lazy-HTMX element + tag w partialu; testy matrycy progu; deploy.

**Poza zakresem:** cykliczność (v1.x); scheduled job/Celery; email/push; nowa generacja/prompt (reuse S-04); konfigurowalny próg; osobny model proaktywnych; zmiana on-demand flow.

## Architektura / Podejście

`DashboardView` liczy `auto_recommendation_due(user)` = (`HabitExecution` distinct dates ≥7) AND (brak `Recommendation(proactive=True)`). Gdy due, partial renderuje element `hx-post=recommendation/auto/ hx-trigger=load` → `RecommendationAutoView` re-sprawdza guard, woła `generate_recommendation(user)` (reuse S-04), persistuje `proactive=True`, zwraca partial z rekomendacją + tag „Automatyczna". Jednorazowość przez istnienie wiersza proaktywnego; cicha porażka nie zapisuje → retry następnym wejściem. Izolacja: próg i generacja po `request.user`.

## Fazy w skrócie

| Faza | Co dostarcza | Kluczowe ryzyko |
|---|---|---|
| 1. Pole + próg + auto-view + dashboard | Auto-rekomendacja działa lokalnie (lazy HTMX, tag, jednorazowość) | Guard jednorazowości; lazy-trigger raz na load; izolacja progu |
| 2. Testy + deploy | Matryca progu (mock) + prod smoke | Migracja 0004; brzeg progu; cicha porażka |

**Wymagania wstępne:** S-04 (maszyneria rekomendacji + OpenRouter env na prod) ✓.
**Szacowany nakład pracy:** ~2 sesje w 2 fazach (duży reuse S-04).

## Otwarte ryzyka i założenia

- Próg liczy distinct daty logowań globalnie usera — user z 7 nawykami w 1 dniu NIE kwalifikuje się (świadome: „7 dni", nie „7 wykonań").
- Cicha porażka może próbować przy każdym wejściu póki OpenRouter leży — akceptowalne (rzadkie, jednorazowe per user).

## Kryteria sukcesu (podsumowanie)

- User po ≥7 dniach logowań dostaje rekomendację automatycznie, raz, bez klikania (tag „Automatyczna").
- Próg liczony tylko z danych usera; jednorazowość wymuszona; błąd cichy (dashboard nietknięty).
- Pełna matryca progu zielona (mock) + prod smoke z realną auto-rekomendacją.
