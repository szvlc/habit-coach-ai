---
project: HabitCoach AI
researched_at: 2026-05-24
recommended_platform: Render
runner_up: Fly.io
context_type: mvp
tech_stack:
  language: Python 3.12
  framework: Django 6.0
  runtime: WSGI (gunicorn) with uv-managed deps
external_services:
  database: Supabase Postgres
  ai_gateway: OpenRouter
---

## Rekomendacja

**Wdróż HabitCoach AI na Render.com (Web Service, Starter plan, Frankfurt EU region).**

Decyzja oparta na dwóch sygnałach: (a) natywne wsparcie `uv` w Render's Python runtime od mid-2025 (bez Dockerfile, bez ręcznych adapterów) plus oficjalny MCP server GA od sierpnia 2025 i opublikowany `llms.txt` / `llms-full.txt` plasują Rendera na najwyższym poziomie agent-friendly criteria spośród viable kandydatów; (b) atomowe migracje przez `preDeployCommand` w `render.yaml` dają deterministyczną bramkę między `git push` a żywą aplikacją, dokładnie dopasowaną do tempa pracy solo-developera. Frankfurt EU region (GA od 2021) obsługuje target_scale = small users w PL/CEE z akceptowalną latencją. Hint `deployment_target: fly` z `tech-stack.md` był miękkim sygnałem z Lekcji 2 — został świadomie nadpisany na podstawie aktualnego researchu pokazującego, że Render dogonił Fly.io na froncie Django i wyprzedził go w wymiarze agent-friendliness.

## Porównanie platform

| Platforma | CLI-first | Zarządzane / Serverless | Dokumentacja agent | Skryptowalne API | MCP / AI | Razem |
|---|---|---|---|---|---|---|
| **Render** (rekomendowany) | Pass | Partial | **Pass** | Pass | **Pass** | **4P / 1Pa** |
| **Vercel** (runner-up #2) | Pass | Pass | **Pass** | Pass | Partial | **4P / 1Pa** |
| **Railway** | Pass | Partial | Partial | Pass | Pass z caveatem | **3P / 2Pa** |
| **Fly.io** (runner-up #1) | Pass | Partial | **Fail** | Pass | Partial | **2P / 2Pa / 1Fa** |
| Cloudflare Workers | — | — | — | — | — | **HARD-FILTERED** |
| Netlify | — | — | — | — | — | **HARD-FILTERED** |

**Twarde filtry**: Cloudflare Workers (V8 isolates, brak runtime'u Pythona dla WSGI) i Netlify (Functions JS-first, brak wspieranej ścieżki dla pełnego Django) zostały wyeliminowane na poziomie filtra runtime'u — żadna ocena nie odwróci tego rozstrzygnięcia.

### Platformy na krótkiej liście

#### 1. Render — Zalecana

- **Native `uv` support** w Python runtime (Render Changelog, mid-2025). Detect `uv.lock` → `uv sync --frozen`. Brak Dockerfile, brak ręcznych adapterów.
- **MCP server GA** od sierpnia 2025 (`https://mcp.render.com/mcp`, HTTP+Bearer, 20+ tools: deploy, scale, logs, metrics, DB query). Dokumentowana integracja z Claude Code.
- **Agent-readable docs**: `render.com/docs/llms.txt` + `llms-full.txt` (regenerowane 2026-04-16), per-page markdown przez `.md` suffix lub `Accept: text/markdown`.
- **`render.yaml` Blueprints** (GA): IaC dla services + envs + `preDeployCommand` (atomowy migrate przed deployem; failure blokuje deploy).
- **EU Frankfurt region** (GA od 2021, sole EU region).
- **Starter $7/mo** (always-on, 512MB, ~50GB egress) — minimum praktyczne; free tier 60s+ cold start łamie PRD NFR dla FR-013 (<10s budget).
- CLI: mature, OpenAPI 3.0 REST API, deploy + rollback endpoints.

#### 2. Fly.io — Runner-up (pre-mortem podniósł go ponad punktację)

- **Dedicated-CPU plans** są tańsze niż Render Starter dla tej samej obwiedni perf pod burst loadem — pre-mortem ujawnił to jako realne ryzyko dla Render w miesiącu 3 jeśli aplikacja zyska 200+ użytkowników szybciej niż oczekiwano.
- **Brak natywnego `uv`** (community thread 2025-04-18, brak ETA) → wymaga hand-written Dockerfile z `uv sync --frozen --no-cache` LUB tymczasowego eksportu `requirements.txt`.
- **Brak llms.txt** (HTML-only docs) i **experimental MCP** (`flyctl mcp server` + `superfly/flymcp` ~4 commits) → niższa pozycja na osi agent-friendly.
- **Brak native PR/preview apps** — wymaga community GitHub Action `superfly/fly-pr-review-apps`.
- **EU Frankfurt** (`fra`) GA, ~150-250ms RTT improvement dla użytkowników PL.
- Mature flyctl, GraphQL + Machines REST API, `fly secrets`, `fly logs`, `fly releases rollback`.

#### 3. Vercel — Runner-up #2 (najlepsza agent-ergonomia, najwyższy operational tax)

- **Django jako first-class framework** od kwietnia 2026 (auto-detect `manage.py`, auto-`collectstatic`, full-stack templates). Cała aplikacja jako jedna Vercel Function na Fluid Compute (GA).
- **Najlepsze agent-docs** (Vercel napisał spec llms.txt). MCP Beta od lutego 2026 (`https://mcp.vercel.com`).
- **Operational tax**:
  - Hobby = non-commercial only (Fair Use enforced) → **Pro $20/seat/mo obowiązkowy** od dnia komercjalizacji.
  - Migracje wymagają **zewnętrznego runnera** (laptop/CI przeciw Supabase direct port 5432) — brak Vercel-native release-runner.
  - **Obowiązkowy Supavisor pooler na port 6543 + transaction mode + `OPTIONS={"prepared_statements": False}`** w psycopg3, bo serverless fan-out wyczerpie Postgres connections direct.
  - FS read-only — bez media uploadów (OK dla HabitCoach: tylko tekst AI).
  - 4.5MB payload cap (OK dla danych nawyków).

## Weryfikacja krzyżowa anty-uprzedzeniowa: Render

### Adwokat diabła — Słabe strony

1. **Frankfurt = jedyny EU region** — brak multi-AZ, brak intra-Render failover. Status page pokazał ≥2 region-wide incydenty FRA w ostatnich 18 miesiącach.
2. **`preDeployCommand` blokuje deploy przy failed migration, ale Postgres zostaje w stanie częściowo zmigrowanym** — Render nie auto-wycofuje DB. App-vs-DB drift to realny tryb awarii.
3. **MCP bearer token = workspace-wide kompromitacja** przy wycieku. HTTP transport gorszy security-wise niż locally-authenticated alternatywy (jak flyctl CLI auth).
4. **Native `uv` jest świeży** (~mid-2025, ~10 miesięcy historii). Krótki changelog entry, edge cases w nietypowych `pyproject.toml` mogą się pojawić.
5. **Free tier 60s+ cold start łamie PRD NFR FR-013** (<10s budget) — Starter $7/mo to *praktyczny minimum*, nie "spróbuj za darmo".
6. **Whitenoise + ManifestStaticFilesStorage** — brakujący referenced asset → migrate OK, render 500 w prod. Klasyczna pułapka Django-on-PaaS.

### Pre-Mortem — Jak to mogło się nie udać (6 miesięcy w przód)

Zespół wdrożył Django 6.0 + Supabase + OpenRouter na Render Starter ($7/mo) i przepchnął MVP w 3 tygodniach. Miesiąc 3: po wzmiance na Polish-tech Reddicie, 200 beta-testerów uderzyło w aplikację. FR-013 generation latency wzrósł z 4s do 18s średnio. Diagnoza: Django `CONN_MAX_AGE=0` (default) + pamięć przeciążona na Starter 512MB → Python proces recykluje co kilka requestów → każdy request otwiera fresh TLS connection do Supabase. Dodanie Supavisor pooler na porcie 6543 (transaction mode) rozwiązało problem, ale wymagało nauki tej samej dyscypliny, którą zespół myślał, że jest „tylko Vercelowa". Równolegle OpenRouter wystrzelił do $80/mc, bo zespół defaultował na drogi model, a Render Logs nie pozwalał łatwo korelować Render request IDs z telemetrią OpenRouter. Miesiąc 4: zespół zmigrował na Fly.io (oryginalna rekomendacja tech-stacka!), bo Whitenoise compression na Render shared CPU okazał się bottleneckiem przy burst load. Migracja zajęła 2 tygodnie. Decyzja na Render nie była zła technicznie; była przedwczesna w stosunku do *konkretnej* ścieżki obciążeniowej.

### Nieznane niewiadome

- **Free tier jest UNUSABLE dla FR-013** — 60s+ cold start vs NFR <10s. Starter $7/mo od dnia pierwszego, nie ma „test na free".
- **Supabase + Render + Django wymaga Supavisor pooler discipline pod burst loadem** — nie tylko Vercel-serverless problem. Każdy shared-CPU PaaS robi to samo przy źle skonfigurowanym `CONN_MAX_AGE`.
- **Render MCP bearer token = workspace-wide compromise** przy wycieku. Rotuj po każdej sesji z wrażliwymi operacjami; Render nie ma per-tool scoped tokens jeszcze.
- **`preDeployCommand` failure dla `migrate` zostawia Supabase w stanie częściowo zmigrowanym** — trzymaj `supabase db dump` backup przed każdym `git push` do main.
- **EU Frankfurt ≠ EU sovereignty** — Render Inc. jest US, CLOUD Act stosuje się do danych w FRA. Habit tracking = potencjalnie dane wrażliwe per GDPR Art. 9; konsultacja prawna przed publicznym startem.

## Historia operacyjna

- **Preview deployments**: Render Preview Environments per PR (GA). Każdy PR open generuje URL `<service>-pr-<num>.onrender.com`; teardown automatyczny przy PR close/merge. **Caveat**: preview env dziedziczy bazową `render.yaml`, więc trzeba świadomie wyłączyć preDeployCommand lub wskazać alternatywny DB (Supabase shadow branch), inaczej każdy PR migruje produkcyjny Postgres.
- **Sekrety**: Render Environment Variables — workspace + service-scope. Sealed values (write-only po set). Rotacja: dashboard lub `render env set <key> <value>` przez CLI. **Twarde guardraile**: `DJANGO_SECRET_KEY`, `DATABASE_URL` (Supabase Supavisor pooler port 6543), `OPENROUTER_API_KEY` — nigdy w `settings.py`, zawsze z `os.environ`.
- **Rollback**: `render deploys rollback <deploy-id>` (CLI) lub dashboard one-click. **Caveat data-side**: Render wycofuje kod aplikacji, ale NIE wycofuje migracji Postgres. Backup `supabase db dump` przed każdym deployem z migracją to obowiązkowy nawyk; bez niego rollback po niekompatybilnej migracji wymaga ręcznego SQL.
- **Approval**: Render auto-deploy on push do main jest default. **Człowiek wymagany** dla: (a) rotacji `DJANGO_SECRET_KEY` (wymaga jednoczesnego invalidate wszystkich sesji + redeploy), (b) zmiany planu (free→starter→plus i wstecz), (c) usunięcia service'u (bez undo), (d) migracji destrukcyjnych (`DROP TABLE`, `ALTER COLUMN ... DROP`). Agent może wykonywać deploy, scale, log read, env list — wszystko reversible bez utraty danych.
- **Logi**: `render logs <service> --tail` (live), `render logs <service> --start <ts> --end <ts>` (historyczne). MCP tool `get_logs` dla agent-readable JSON. Render Logs UI w dashboardzie ma 30-day retention na Starter. Korelacja request-id ↔ OpenRouter usage wymaga własnego middleware Django logging tracking_id z OpenRouter response headers.

## Rejestr ryzyka

| Ryzyko | Źródło | Prawdopodobieństwo | Wpływ | Łagodzenie |
|---|---|---|---|---|
| Free tier cold start 60s+ łamie PRD NFR FR-013 (<10s) | Adwokat diabła + Unknown unknowns | Wysokie (jeśli zostaniesz na free) | Wysoki | Starter $7/mo od dnia pierwszego; budżetuj $7-15/mo compute jako koszt wejścia, nie "później" |
| Connection pool exhaustion Supabase pod burst loadem | Pre-mortem | Średnie (zależy od skali) | Wysoki | Konfiguruj `DATABASE_URL` przez Supavisor pooler port 6543 (transaction mode) od początku; `CONN_MAX_AGE=600` w `DATABASES['default']` |
| Failed `preDeployCommand` migration → Supabase częściowo zmigrowany | Adwokat diabła + Unknown unknowns | Niskie-średnie | Wysoki | `supabase db dump > backups/pre-<commit>.sql` przed `git push` do main; test migracji na Supabase shadow branch lokalnie |
| Render MCP bearer token leak = workspace-wide compromise | Adwokat diabła + Unknown unknowns | Niskie (jeśli rotujesz) | Krytyczny | Rotuj token po sesjach agenta dotykających prod; rozważ Render organization tokens gdy będą dostępne; nigdy nie pasteuj tokena do publicznego transcriptu |
| EU Frankfurt outage → brak intra-Render failover | Adwokat diabła | Niskie (rzadkie, ale historyczne) | Średni | Akceptujemy dla MVP; status page subscribe; backup Supabase i kod w GitHub (poza Renderem) |
| Whitenoise ManifestStaticFilesStorage missing asset → 500 w prod | Adwokat diabła | Niskie (z dobrym CI testem) | Średni | `python manage.py collectstatic --dry-run` jako CI step przed merge; `render.yaml` buildCommand zawiera `collectstatic --no-input` |
| OpenRouter koszty wystrzelą bez korelacji z Render usage | Pre-mortem | Średnie | Średni (budgetary) | OpenRouter budget alert $20/mo; default model = `anthropic/claude-haiku-4-5` lub `openai/gpt-4o-mini`, NIE gpt-4 dla FR-013; log `openrouter-request-id` w Django middleware dla korelacji |
| Whitenoise compression CPU bottleneck na Starter shared CPU | Pre-mortem | Średnie pod burst loadem | Średni | Monitoruj Render service metrics CPU%; przygotuj migrację do Render Plus ($25/mo, dedicated CPU) lub Fly.io shared-cpu-2x jako exit ramp |
| EU Frankfurt ≠ EU sovereignty (CLOUD Act) | Unknown unknowns | Średnie (legal exposure) | Średni-wysoki (legal) | Konsultacja prawna przed publicznym startem; data residency policy w privacy notice |
| `uv` native support edge cases (niedojrzały, ~10mo) | Adwokat diabła | Niskie-średnie | Niski-średni (recoverable) | Exit ramp do Dockerfile-based deploy zawsze gotowy; pin `uv` version w `.tool-versions` |
| Hard-filtered Cloudflare familiarity (Q3) nie przenosi się na Render | Wynik wywiadu vs research | Pewne | Niski (learning curve) | Spodziewaj się ~1-2 dni nauki render.yaml + Blueprints. Docs są dobre. |

## Rozpoczęcie pracy

Konkretne pierwsze kroki do wdrożenia HabitCoach AI na Render. Każdy krok zweryfikowany pod kątem Django 6.0 + uv (a nie ogólnego Python tutorial).

1. **Włącz Render account + zainstaluj CLI**: `npm i -g @render/cli` (lub `brew install render`); `render login` → przeglądarka OAuth. Sprawdź zalogowanie: `render whoami`.
2. **Utwórz `render.yaml` w katalogu głównym repozytorium** (Blueprint IaC, alternatywa dla klikania w dashboard):
   ```yaml
   services:
     - type: web
       name: habit-coach-ai
       runtime: python
       plan: starter
       region: frankfurt
       buildCommand: "uv sync --frozen && uv run python manage.py collectstatic --no-input"
       startCommand: "uv run gunicorn habit_coach_ai.wsgi:application --bind 0.0.0.0:$PORT"
       preDeployCommand: "uv run python manage.py migrate --no-input"
       envVars:
         - key: PYTHON_VERSION
           value: "3.12"
         - key: DJANGO_SECRET_KEY
           sync: false
         - key: DATABASE_URL
           sync: false
         - key: OPENROUTER_API_KEY
           sync: false
         - key: ALLOWED_HOSTS
           value: ".onrender.com"
   ```
3. **Dostosuj `habit_coach_ai/settings.py`** przed pierwszym deployem:
   - `SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]` (usuń startproject default)
   - `DEBUG = os.environ.get("DEBUG", "False").lower() == "true"`
   - `ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")`
   - `DATABASES['default'] = dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=600)` (z `dj-database-url` package — `uv add dj-database-url`)
   - Whitenoise middleware: `'whitenoise.middleware.WhiteNoiseMiddleware'` zaraz po `SecurityMiddleware` (`uv add whitenoise`)
   - `STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'`
4. **Przygotuj Supabase Postgres jako external DB**: utwórz projekt na supabase.com (EU region — Frankfurt match), skopiuj `Connection string > Transaction pooler` (port 6543) — to wartość dla `DATABASE_URL`. NIE używaj direct port 5432 dla aplikacji.
5. **Pierwszy deploy**: `git push origin main` (po `git init` + commit + remote). Render czyta `render.yaml`, autostart build + migrate + start. Monitoruj live: `render logs habit-coach-ai --tail`. Po zielonym deploy: `https://habit-coach-ai.onrender.com` powinien zwrócić Django default page.
6. **Konfiguracja MCP do Claude Code** (jednorazowo): `claude mcp add --transport http render https://mcp.render.com/mcp --header "Authorization: Bearer <RENDER_API_KEY>"`. Klucz: dashboard → Account Settings → API Keys. Test: `claude` → `/mcp` → `render` powinien pokazać tools jak `list_services`, `trigger_deploy`, `get_logs`.

## Poza zakresem

W niniejszych badaniach **nie** oceniano:

- Konfiguracji obrazu Docker (Render Python runtime natywnie obsługuje `uv` — Dockerfile zbędny).
- Konfiguracji potoku CI/CD poza Render auto-deploy on push (GitHub Actions integration tech-stack hint `auto-deploy-on-merge` realizowany przez native Render Git integration).
- Architektury na skalę produkcyjną — multi-region, HA Postgres, dedicated CPU dla ≥10k DAU, dedicated Redis cache. Te decyzje pojawią się dopiero po PMF (post-MVP).
- Wyboru modelu OpenRouter — `tech-stack.md` mówi `has_ai: true`, ale konkretny LLM (Claude vs OpenAI vs open-weights) to decyzja produktowa do FR-011/FR-013 implementation phase.
- GDPR Article 30 record-of-processing, DPA z Supabase i OpenRouter, processor agreements — legal scope, wymaga prawnika.
