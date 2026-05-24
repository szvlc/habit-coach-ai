---
project: "HabitCoach AI"
context_type: greenfield
created: 2026-05-19
updated: 2026-05-19
product_type: web-app
target_scale:
  users: small
  qps: low
  data_volume: small
timeline_budget:
  mvp_weeks: 3
  hard_deadline: null
  after_hours_only: true
checkpoint:
  current_phase: 8
  phases_completed: [1, 2, 3, 4, 5, 6, 7]
  gray_areas_resolved:
    - topic: "persona scope"
      decision: "osoba pracująca umysłowo 25–40, próbująca samodzielnie wdrażać nawyki samorozwojowe"
    - topic: "pain category"
      decision: "brak inteligentnej informacji zwrotnej — historia bez znaczenia"
    - topic: "moment of pain"
      decision: "po 2–3 tygodniach logowania, gdy historia jest, ale nie wynika z niej nic"
    - topic: "insight vs status quo"
      decision: "AI rekomenduje na bazie konkretnych danych użytkownika, nie generycznie"
    - topic: "auth strategy"
      decision: "email + hasło z resetem przez link"
    - topic: "role model"
      decision: "płaski; jeden typ użytkownika, widzi tylko swoje dane"
    - topic: "MVP flow scope"
      decision: "6 kroków: rejestracja → dodanie nawyku → log wykonania → powtarzanie → widok 30-dni → generowanie rekomendacji AI"
    - topic: "timeline budget"
      decision: "3 tygodnie after-hours work, zakres potwierdzony jako realny"
    - topic: "secondary success"
      decision: "powroty ≥ 4/tydzień"
    - topic: "guardrail (sole)"
      decision: "prywatność: dane jednego usera niedostępne innym"
  frs_drafted: 13
  quality_check_status: accepted
---

# HabitCoach AI — shape notes

Seed idea (from `idea-notes.md`): inteligentna informacja zwrotna dla osób śledzących nawyki, generowana przez AI na podstawie historii wykonań, mająca zapobiec porzucaniu aplikacji po 2–3 tygodniach. MVP web-only.

## Vision & Problem Statement

Osoby pracujące umysłowo (25–40 lat) próbują budować nawyki samorozwojowe — medytacja, czytanie, sport — i po 2–3 tygodniach systematycznego logowania widzą w aplikacji historię wykonań, ale nie potrafią nic z niej wywnioskować. Dane są obecne; znaczenie — nie. Wykresy i streaki zamieniają się w pustą presję bez wskazówki, co dalej, i użytkownik rezygnuje, mimo że aplikacje do śledzenia są dostępne.

Insight: konkurencja albo nie używa AI, albo serwuje generyczne porady ("pij więcej wody", "śpij 8 godzin") niezwiązane z realnymi danymi konkretnej osoby. HabitCoach AI generuje rekomendacje odnoszące się do faktycznych wzorców tego konkretnego użytkownika — to różnicuje produkt względem statusu quo i adresuje zidentyfikowany moment porzucenia.

## User & Persona

Osoba pracująca umysłowo, 25–40 lat, czytelnik literatury self-help / produktywności, próbująca samodzielnie wdrożyć kilka nawyków samorozwojowych (np. medytacja, czytanie, regularny ruch). Średnio zmotywowana, decyzję podjęła sama, próbowała już wcześniej innych aplikacji do śledzenia nawyków, ale odpadała po 2–3 tygodniach kiedy logowanie zaczyna wydawać się jałowe.

## Access Control

Uwierzytelnianie: email + hasło. Rejestracja konta, logowanie, możliwość odzyskania hasła (reset przez link na email). Sesja użytkownika utrzymywana po zalogowaniu.

Model ról: płaski. Jeden typ użytkownika; każdy widzi i edytuje wyłącznie własne nawyki, własną historię wykonań i rekomendacje wygenerowane dla siebie. Brak admina, brak udostępniania, brak ról płatnych w MVP.

Niezalogowany odwiedzający strony aplikacji: widzi ekran rejestracji / logowania; każda gated trasa przekierowuje do logowania.

## Success Criteria

### Primary
- ≥ 75 % rekomendacji wygenerowanych przez AI odnosi się do konkretnych danych historycznych zalogowanego użytkownika, a nie do generycznych porad.
- Użytkownicy logują wykonania nawyków przez co najmniej 2 tygodnie od rejestracji, nie porzucając aplikacji w tym czasie.

### Secondary
- Użytkownik wraca do aplikacji ≥ 4 razy w tygodniu (sygnał operacyjnego zaangażowania; sam w sobie nie wystarcza bez kryteriów Primary).

### Guardrails
- Dane nawyków, historii wykonań i rekomendacji jednego użytkownika nie są dostępne żadnemu innemu użytkownikowi ani niezalogowanemu odwiedzającemu.

## Functional Requirements

### Authentication
- FR-001: Niezalogowany użytkownik może zarejestrować konto podając email i hasło. Priority: must-have
  > Socrates: Kontrargument rozważony: "magic link / passwordless byłby skończeniem szybszy, wyeliminowałby reset hasła". Rezolucja: zostaje email+hasło — to nadal standard webowy i nie wymaga konfiguracji wysyłki e-mail przy onboardingu (reset jest osobnym FR).
- FR-002: Zarejestrowany użytkownik może się zalogować emailem i hasłem; sesja jest długa (remember-me domyślnie). Priority: must-have
  > Socrates: Kontrargument rozważony: "bez remember-me / długiej sesji user loguje się codziennie i odpada szybciej". Rezolucja: FR zaktualizowane — długa sesja staje się częścią FR-a, nie odrębnym założeniem.
- FR-003: Zarejestrowany użytkownik może zresetować zapomniane hasło przez link wysłany na email. Priority: must-have
  > Socrates: Kontrargument rozważony: "reset wymaga konfiguracji wysyłki email — 1-2 dni dodatkowej pracy w MVP". Rezolucja: zostaje must-have, bo długoterminowo brak resetu = utrata konta = utrata użytkownika.
- FR-004: Zalogowany użytkownik może się wylogować. Priority: nice-to-have
  > Socrates: Kontrargument rozważony: "wylogowanie nie ma znaczenia w MVP single-device". Rezolucja: demotowane do nice-to-have — sesja sama wygasa, wylogowanie wchodzi jeśli starczy czasu.

### Habit management
- FR-005: Zalogowany użytkownik może dodać nowy nawyk z nazwą (wykonywany codziennie). Priority: must-have
  > Socrates: Kontrargument rozważony: "częstotliwość 'N razy w tygodniu' komplikuje logikę". Rezolucja: zakres wycięty — w MVP wszystkie nawyki są codzienne; częstotliwości X-razy-w-tygodniu odłożone do v2.
- FR-006: Zalogowany użytkownik może edytować nazwę istniejącego nawyku. Priority: must-have
  > Socrates: Brak kontrargumentu wybranego. Rezolucja: zostaje — brak edycji frustruje natychmiast przy literówce.
- FR-007: Zalogowany użytkownik może zarchiwizować nawyk (nawyk znika z list aktywnych, historia wykonań zachowana dla AI). Priority: must-have
  > Socrates: Kontrargument rozważony: "twarde usuwanie z historią traci dane dla AI". Rezolucja: FR zmienione z 'usuń' na 'zarchiwizuj' — historia zostaje, AI ma większą bazę. Hard delete (np. GDPR) odłożone.

### Execution logging
- FR-008: Zalogowany użytkownik może jednym kliknięciem oznaczyć nawyk jako wykonany w bieżącym dniu. Priority: must-have
  > Socrates: Brak kontrargumentu wybranego. Rezolucja: zostaje — 1 klik to fundamentalna obietnica MVP.
- FR-009: Zalogowany użytkownik może cofnąć (odznaczyć) zalogowane wykonanie tylko dla bieżącego dnia; wsteczne dodawanie/cofanie zablokowane. Priority: must-have
  > Socrates: Kontrargument rozważony: "swobodne cofanie pozwala fałszować streaki — AI uczy się z fałszu". Rezolucja: zakres ograniczony tylko do dnia bieżącego; wsteczne operacje zablokowane.

### History
- FR-010: Zalogowany użytkownik może przeglądać historię wykonań każdego nawyku za ostatnie 30 dni. Priority: must-have
  > Socrates: Kontrargument rozważony: "30 dni za dużo, tygodniowy kalendarz wystarczy". Rezolucja: zostaje 30 dni — AI potrzebuje dłuższej historii, by rekomendacje były specyficzne.

### AI recommendations
- FR-011: Zalogowany użytkownik może na żądanie wygenerować rekomendację AI opartą o swoją historię nawyków. Priority: must-have
  > Socrates: Kontrargument rozważony: "klikanie to tarcie — rekomendacja powinna pojawiać się sama". Rezolucja: FR-011 (on-demand) zostaje; dodajemy FR-013 (proaktywna, po pierwszym progu danych).
- FR-012: Zalogowany użytkownik widzi ostatnią wygenerowaną dla siebie rekomendację po powrocie do aplikacji. Priority: must-have
  > Socrates: Kontrargument rozważony: "pełna historia rekomendacji jest niezbędna do porównania". Rezolucja: w MVP wystarczy ostatnia — historia rekomendacji odłożona do v2.
- FR-013: Aplikacja automatycznie generuje pierwszą rekomendację AI po osiągnięciu progu danych (≈ 7 dni logowań dla co najmniej jednego nawyku); użytkownik widzi ją bez konieczności klikania. Priority: must-have
  > Socrates: FR dodany jako rezolucja FR-011 — aby produkt sam pierwszą raz pokazał, że "coś z tych danych wynika".

## User Stories

### US-01: Pierwsza pełna sesja użytkownika prowadząca do rekomendacji

- **Given** osoba zainteresowana budowaniem nawyków, bez konta w HabitCoach AI
- **When** zarejestruje konto, doda przynajmniej jeden nawyk, zaloguje wykonania przez co najmniej kilka–kilkanaście dni, otworzy widok historii i kliknie "Wygeneruj rekomendację"
- **Then** zobaczy rekomendację wygenerowaną przez AI odnoszącą się do swoich konkretnych danych historycznych (np. wzorca wykonań, dni słabszych, najbardziej spójnych nawyków)

#### Acceptance Criteria
- Rejestracja działa w jednym ekranie (email + hasło + ewentualnie potwierdzenie)
- Po rejestracji użytkownik trafia bezpośrednio na ekran dodawania pierwszego nawyku (zero pustego dashboardu)
- Logowanie wykonania nawyku to dokładnie jedno kliknięcie z natychmiastowym wizualnym potwierdzeniem
- Widok historii pokazuje 30 dni dla każdego nawyku w sposób umożliwiający zobaczenie wzorca (np. siatka dni z oznaczeniem wykonane/niewykonane)
- Generowanie rekomendacji jest jednym kliknięciem; wynik pojawia się w sposób kontekstowy (modal, panel, osobny ekran) i odnosi się do nazwy nawyku użytkownika lub konkretnego wzorca wykonania
- Pusty dashboard (brak nawyków) i pusta historia (brak logowań) mają explicit empty-state z instrukcją następnego kroku

## Business Logic

Aplikacja analizuje historię wykonań nawyków konkretnego użytkownika i generuje dla niego rekomendacje odnoszące się do zidentyfikowanych w jego danych wzorców — nie generyczne porady.

Wejście reguły to: lista aktywnych nawyków danego użytkownika (nazwy + częstotliwość codzienna), historia logowanych wykonań tych nawyków (znacznik wykonania per dzień, do 30 dni wstecz) oraz okres obowiązywania konta. Wyjście: pojedynczy tekst rekomendacji, w którym co najmniej 75 % treści odnosi się do konkretnych elementów wejścia (np. nazw nawyków użytkownika, dni słabszych w jego historii, najbardziej spójnych nawyków, niedawnych przerw w streaku) zamiast do uniwersalnych porad ("śpij więcej", "pij wodę").

Użytkownik napotyka rekomendację w dwóch momentach: (a) gdy świadomie ją wygeneruje przyciskiem (FR-011), (b) gdy aplikacja sama ją pokaże po osiągnięciu progu zbioru danych (FR-013). Po zobaczeniu rekomendacji użytkownik wraca do dashboardu i kontynuuje logowanie nawyków — nie ma w MVP innych przepływów oddzielnie zarządzających rekomendacjami.

## Non-Functional Requirements

- Logowanie wykonania nawyku jest potwierdzane wizualnie w mniej niż 200 ms od kliknięcia, niezależnie od liczby istniejących nawyków i długości historii.
- Rekomendacja AI generowana na żądanie staje się widoczna dla użytkownika w mniej niż 10 sekund od kliknięcia "Wygeneruj"; jeżeli generacja zajmuje dłużej, użytkownik otrzymuje widoczny postęp / stan pośredni co najmniej co 2 sekundy.

## Non-Goals

- Powiadomienia push i email — brak wieczornych przypomnień; logowanie nawyków zależy wyłącznie od inicjatywy użytkownika.
- Integracje z zewnętrznymi platformami (Google Fit, Apple Health, Garmin) — brak automatycznego logowania snu / treningu z urządzeń zewnętrznych.
- Gamifikacja (punkty, odznaki, rankingi, poziomy) — brak warstwy nagród poza widokiem własnej historii.
- Aplikacje mobilne (iOS, Android) — MVP jest tylko web; aplikacje natywne odłożone.
- Współdzielenie nawyków między użytkownikami (link-share, team workspaces, publiczny profil) — produkt pozostaje single-user.

## Open Questions

1. **Próg danych dla automatycznej rekomendacji (FR-013)** — wstępnie ≈ 7 dni logowań dla co najmniej jednego nawyku, ale precyzyjna definicja (czy "co najmniej jednego" wystarczy? jaki minimum count wykonań?) wymaga doprecyzowania w PRD lub na etapie planu implementacji.
2. **Sposób pomiaru kryterium "75 % rekomendacji odnosi się do konkretnych danych użytkownika"** — czy weryfikacja jest manualna (przegląd próbki rekomendacji), automatyczna (np. sprawdzenie, że rekomendacja zawiera nazwę nawyku użytkownika lub konkretny token z danych), czy obie? Wymaga decyzji przed startem MVP, by mierzyć Primary success.
3. **Częstotliwość rekomendacji automatycznej (FR-013)** — czy aplikacja generuje proaktywną rekomendację tylko raz po osiągnięciu progu, czy regularnie (np. co N dni / co tydzień)?

## Quality cross-check

Cross-check zakończony bez luk (status: accepted). Wszystkie wymagane elementy obecne:

- Access Control: present
- Business Logic (one-sentence rule): present
- Project artifacts: present
- Timeline-cost acknowledged: present (mvp_weeks = 3, w domyślnym budżecie skill)
- Non-Goals: present (5 pozycji)
- Preserved behavior: n/a (greenfield)
