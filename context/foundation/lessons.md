# Lessons Learned

> Append-only register of recurring rules and patterns. Re-read at start by /10x-frame, /10x-research, /10x-plan, /10x-plan-review, /10x-implement, /10x-impl-review.

## Success-criteria sign-off must actually read the command output

- **Context**: Surfaced during retro of register-and-login (S-01). Plan
  §Phase 4 / Automated #4.2 said `manage.py check --deploy — brak critical
  warnings` and was marked `[x]` in commit `d3419ba`. Re-running today emits
  5 warnings; 4 are real (cookie Secure flags, SSL redirect, HSTS). F1
  (critical production security gap) would have been caught at Phase 4 if
  this criterion had been read literally.

- **Problem**: Success criteria written as "command X passes" or "no critical
  warnings" can be ticked without anyone parsing the actual output. The word
  "critical" is especially treacherous — Django doesn't classify check
  warnings by severity, so the gate becomes subjective and degrades to
  "did the command exit 0".

- **Rule**: <fill in — proposed: any non-zero warning count from an
  automated-verification command is a Phase fail unless the checkbox is
  annotated `[x] (accepted: <why>)`. Write criteria as "output contains
  exactly these warnings: <enumerate>, nothing else" rather than "no
  critical warnings".>

- **Applies to**: <fill in — proposed: every `/10x-plan` automated-verification
  checklist; every `/10x-implement` and `/10x-impl-review` gate that consumes
  one; especially Django/Rails `check --deploy`-style commands that surface
  many warnings of varying severity.>

## Egzekwuj wielopolowy UniqueConstraint jawnie w formularzu, nie przez validate_unique

- **Context**: Każdy Django ModelForm walidujący unikalność, gdzie część pól constraintu jest ustawiana poza formularzem (np. `user` w `form_valid`/`get_form_kwargs`); modele z `UniqueConstraint` na wielu polach.
- **Problem**: `ModelForm.validate_unique()` wyklucza pola spoza formularza, więc `UniqueConstraint` obejmujący takie pole (np. `(user, name)`) jest cicho pomijany — duplikat przechodzi walidację i leci do DB → `IntegrityError` 500 zamiast przyjaznego błędu pola. Zdarzyło się w manage-habits S-02 (`HabitForm`).
- **Rule**: Gdy `UniqueConstraint` obejmuje pole ustawiane poza formularzem, nie polegaj na `ModelForm.validate_unique` — przekaż to pole do formularza i sprawdź duplikat jawnie w `clean_<field>` (wykluczając `self.instance.pk` przy edycji), a `UniqueConstraint` w modelu zostaw jako backstop integralności.
- **Applies to**: plan, implement, impl-review

## Integracja zewnętrznego LLM: prod-smoke realnym wywołaniem (mock nie złapie slug/limitów/auth)

- **Context**: Każda faza integrująca zewnętrzny LLM/API gateway (OpenRouter/OpenAI itp.), gdzie testy jednostkowe mockują wywołanie sieciowe.
- **Problem**: W S-04 testy z mockiem LLM przeszły, ale prod padł dwukrotnie: nieprawidłowy slug modelu (`claude-haiku-4-5` vs `-4.5` → 404) i brak `max_tokens` (default ~64k → 402 przy małym saldzie). Mock nie waliduje sluga/limitów/auth realnego gateway.
- **Rule**: Przy integracji zewnętrznego LLM zrób prod-smoke z JEDNYM realnym wywołaniem przed sign-off (mock nie sprawdzi sluga/limitów/auth); zawsze ustaw jawny `max_tokens`; zweryfikuj dokładny slug modelu względem żywej listy modeli dostawcy.
- **Applies to**: plan, implement, impl-review

## Zmiana „tylko styling" musi weryfikować, że nie usuwa zależności runtime (JS/`<script>`)

- **Context**: Każda faza opisana jako „kosmetyczna" / „tylko CSS/styling" edytująca szablon bazowy (np. `base.html`), który ładuje biblioteki JS przez `<script>` (HTMX/Alpine/itp.) i deklaruje atrybuty od nich zależne (`hx-*`).
- **Problem**: Redesign przepisujący `base.html` (commit `2910944`) zgubił `<script>` HTMX, zostawiając atrybuty `hx-*` — rekomendacja AI przestała się odświeżać, a proaktywna auto-rekomendacja nie odpalała. Toggle działał dzięki fallbackowi formularza, co maskowało regresję aż do zgłoszenia użytkownika. Naprawione w `96a31ec`.
- **Rule**: Przy „stylingowych" zmianach szablonu bazowego zweryfikuj, że nie zniknęły tagi `<script>`/zależności JS; dodaj test regresyjny sprawdzający obecność biblioteki na renderowanej stronie (np. `assertContains(response, "htmx.org")`).
- **Applies to**: implement, impl-review

## Zależności frontendowe z CDN: pin dokładnej wersji + SRI przed prod-hardeningiem

- **Context**: Każda strona (zwłaszcza uwierzytelniona) ładująca biblioteki JS/CSS z publicznego CDN (Tailwind Play `cdn.tailwindcss.com`, HTMX/Alpine z `unpkg`/`jsdelivr`).
- **Problem**: Tailwind + HTMX ładowane bez Subresource Integrity i bez pinu dokładnej wersji (`htmx.org@2` = floating major). Kompromitacja/hijack CDN = dowolny JS w sesji użytkownika. Dodatkowo `cdn.tailwindcss.com` jest oficjalnie „not for production" (runtime compile, duży payload).
- **Rule**: Na MVP CDN jest akceptowalny, ale przed prod-hardeningiem przypnij dokładne wersje + dodaj `integrity`/SRI (z `crossorigin`), a Tailwind przenieś do kroku build zamiast runtime CDN.
- **Applies to**: plan, implement, impl-review
