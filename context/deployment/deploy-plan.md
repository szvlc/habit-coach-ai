# Deploy Plan — HabitCoach AI to Render (first production deploy)

## Context

The HabitCoach AI Django scaffold is currently `runserver`-only on `db.sqlite3` with `startproject` defaults (`SECRET_KEY` plaintext, `DEBUG = True`, empty `ALLOWED_HOSTS`). The decision artifact at `@context/foundation/infrastructure.md` chose **Render Web Service, Starter $7/mo, Frankfurt EU region** with external Supabase Postgres (Supavisor pooler) + external OpenRouter for AI calls. This plan turns those decisions into a first deploy.

User has **GitHub account only**; Render, Supabase, and OpenRouter accounts will be created during execution. Repo is not yet under git (`.git/` absent).

Outcome: a publicly reachable `https://habit-coach-ai.onrender.com` that loads Django's admin against a live Supabase Postgres, with secrets in Render env vars and the Render MCP wired into Claude Code for ongoing operations.

## Critical files modified or created

- `pyproject.toml` — add prod deps via `uv add`.
- `habit_coach_ai/settings.py` — env-var refactor (4 fields).
- `.gitignore` — new file at repo root.
- `render.yaml` — new Blueprint IaC at repo root.
- `context/deployment/deploy-plan.md` — final approved copy of this plan (last step, after deploy succeeds).

Files NOT touched: `manage.py`, `habit_coach_ai/{urls,wsgi,asgi}.py`, `context/foundation/*`, `AGENTS.md`, `CLAUDE.md`.

## Approach

Execute in **8 phases**. Each phase has a verification gate; do not proceed if it fails.

### Phase 1 — Local code preparation

1. **Add prod dependencies** (one `uv add` call to batch them):
   ```
   uv add gunicorn whitenoise dj-database-url 'psycopg[binary]'
   ```
   `psycopg` v3 (not psycopg2 — Django 6.0 prefers v3). `[binary]` extra avoids needing libpq dev headers on Render's builder.

2. **Refactor `habit_coach_ai/settings.py`** — replace four sections:
   - `SECRET_KEY`: `os.environ["DJANGO_SECRET_KEY"]` (uncovered key fails fast — better than silent dev fallback).
   - `DEBUG`: `os.environ.get("DEBUG", "False").lower() == "true"`.
   - `ALLOWED_HOSTS`: `os.environ.get("ALLOWED_HOSTS", "").split(",")` with localhost fallback for dev only via `if DEBUG`.
   - `DATABASES`: branch on `DATABASE_URL` presence — if set, use `dj_database_url.parse(..., conn_max_age=600, ssl_require=True)`; otherwise keep SQLite for `manage.py runserver` dev. This preserves the dev loop without forcing Supabase locally.
   - Add WhiteNoise middleware after `SecurityMiddleware`.
   - Set `STATIC_ROOT = BASE_DIR / "staticfiles"` and `STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"`.
   - Add `import os` at top.

3. **Create `.gitignore`** at repo root. Minimum content:
   - `.venv/`, `__pycache__/`, `*.pyc`
   - `db.sqlite3`, `staticfiles/`
   - `.env`, `.env.local`
   - `memory/` (Claude local memory — should not be in repo)
   - `backups/` (for future `supabase db dump` files — never commit DB dumps)
   - **NOT** ignored: `context/`, `.claude/skills/`, `CLAUDE.md`, `AGENTS.md`, `pyproject.toml`, `uv.lock` — these are part of the repo.

4. **Smoke test locally** (still on SQLite):
   ```
   $env:DJANGO_SECRET_KEY = "test-key-not-for-prod"
   uv run python manage.py migrate
   uv run python manage.py runserver
   ```
   Verify `http://127.0.0.1:8000/admin/` returns the Django admin login. If 500, env-var refactor has a bug — fix before continuing.

**Verification gate**: local `runserver` still works with env-vars; admin renders.

### Phase 2 — External service accounts

Three accounts, in this order (each unlocks the next phase's needed values):

1. **Supabase** (DB):
   - Sign up at supabase.com (free tier OK for MVP).
   - Create project: `habit-coach-ai-mvp`, region `eu-central-1` (Frankfurt) to match Render Frankfurt.
   - Wait ~2 min for provisioning.
   - Project Settings → Database → **Connection string → Transaction pooler (port 6543)** → copy. This is the `DATABASE_URL` value. **Must be port 6543, not 5432.**
   - Note: when using Supavisor transaction pooler, add `?sslmode=require` if not already present.

2. **OpenRouter** (AI):
   - Sign up at openrouter.ai.
   - Generate API key (Profile → Keys → Create Key). Name it `habit-coach-render-prod`.
   - Set budget alert: $20/month (Profile → Billing → Spending limits). Without this, a runaway model loop can bill hundreds in hours.
   - Choose default model: `anthropic/claude-haiku-4-5` or `openai/gpt-4o-mini` — both cheap enough for FR-011/FR-013 at MVP scale. **NOT** `gpt-4` / Claude Opus by default (pre-mortem warning).

3. **Render**:
   - Sign up at render.com (GitHub OAuth signup is the smoothest path — also authorizes Render to read your repo in Phase 4).
   - Account Settings → API Keys → Create. Name `habit-coach-claude-code-mcp`. Copy and store securely — needed for MCP wiring in Phase 7.

**Verification gate**: three secrets in hand (`DATABASE_URL`, `OPENROUTER_API_KEY`, Render API key). Do NOT commit any of these.

### Phase 3 — `render.yaml` blueprint

Create `render.yaml` at repo root (per `@context/foundation/infrastructure.md` "Rozpoczęcie pracy" section):

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
      - key: DEBUG
        value: "False"
```

`sync: false` for secrets means Render prompts for them on Blueprint deploy and never logs them — they only live in Render's encrypted store.

**Verification gate**: `render.yaml` parses (validate visually; Render itself will reject malformed YAML in Phase 5).

### Phase 4 — Git repository on GitHub

1. **Generate a Django SECRET_KEY for prod** (one-off, write down for Phase 5):
   ```
   uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
   This is the value for the `DJANGO_SECRET_KEY` secret in Render. Treat it like a password.

2. **Initialize git + first commit**:
   ```
   git init
   git add .
   git status   # sanity: confirm no .env, db.sqlite3, .venv/, memory/ staged
   git commit -m "feat: initial HabitCoach AI scaffold with Render-ready settings"
   ```

3. **Create GitHub repo** (browser): `github.com/new` → name `habit-coach-ai`, private, no README/license (already have files locally).

4. **Push**:
   ```
   git remote add origin https://github.com/<user>/habit-coach-ai.git
   git branch -M main
   git push -u origin main
   ```

**Verification gate**: repo visible on GitHub at the chosen URL, branch `main` shows all files, `db.sqlite3`/`.venv/`/`.env`/`memory/` are absent from the file listing.

### Phase 5 — Render Blueprint deploy (first)

1. Render dashboard → **New +** → **Blueprint** → connect GitHub → select `habit-coach-ai` repo → branch `main`.
2. Render parses `render.yaml`; shows planned service + the 3 secrets it needs (`sync: false`).
3. Enter the three secrets:
   - `DJANGO_SECRET_KEY` = the value generated in Phase 4.1
   - `DATABASE_URL` = the Supavisor pooler URL from Phase 2.1 (port 6543, with `?sslmode=require`)
   - `OPENROUTER_API_KEY` = the key from Phase 2.2
4. Click **Apply** → Render starts the first deploy:
   - `uv sync --frozen` → installs deps
   - `uv run python manage.py collectstatic --no-input` → WhiteNoise compresses statics
   - `uv run python manage.py migrate --no-input` → applies Django migrations to Supabase Postgres (FR: this creates `auth_user`, `django_session`, `auth_group`, etc.)
   - `gunicorn habit_coach_ai.wsgi:application` starts
5. Watch logs live: dashboard "Logs" tab, or `render logs habit-coach-ai --tail` if CLI installed.

**Verification gate**: deploy reports "Live" (green). If it fails:
- `collectstatic` failure → usually `STATIC_ROOT` or `STATICFILES_STORAGE` misconfigured in `settings.py`. Re-check Phase 1.2.
- `migrate` failure → most likely `DATABASE_URL` wrong (port 5432 instead of 6543, missing `sslmode=require`, or wrong project). Re-check Phase 2.1.
- Service start failure → usually `ALLOWED_HOSTS` not including `.onrender.com`. Re-check Phase 1.2 and the env var.

### Phase 6 — Smoke tests against live service

1. Hit `https://habit-coach-ai.onrender.com/admin/` in browser → expect Django admin login form (not 500, not connection refused, not Bad Request).
2. **Create superuser** (one-off via Render Shell): dashboard → service → Shell → run:
   ```
   uv run python manage.py createsuperuser
   ```
   Use a strong password, store it in a password manager. This account is the only way into Django admin until a real auth flow is built per FR-001..003.
3. Log in to `/admin/` with that superuser. Confirm: page renders fully (CSS visible — proves WhiteNoise served statics), no DB errors (proves Supabase connection works), session persists across reload (proves Postgres `django_session` writes work).
4. Check Supabase dashboard → Database → Tables: expect `auth_user`, `django_session`, etc. to be populated.

**Verification gate**: admin reachable, superuser login works, Supabase tables exist with data.

### Phase 7 — Render MCP wiring (Claude Code)

Wire the Render MCP server into Claude Code so future deploys, log inspection, and DB queries can flow through the agent:

```
claude mcp add --transport http render https://mcp.render.com/mcp --header "Authorization: Bearer <RENDER_API_KEY>"
```

where `<RENDER_API_KEY>` is the Render API key from Phase 2.3.

**Verification gate**: in a new `claude` session, `/mcp` lists `render`, and `render.list_services` returns `habit-coach-ai` as Live.

**Security note (from `@context/foundation/infrastructure.md` risk register)**: the bearer token is workspace-wide. Rotate it after any session where it might have been exposed (shared transcript, screenshot). Do not commit it.

### Phase 8 — Persist this plan as the canonical deploy record

After deploy is verified green, copy this approved plan to `context/deployment/deploy-plan.md` (the lesson's canonical artifact path). Create the `context/deployment/` directory if absent. This becomes the audit trail referenced by future milestone-planning skills.

## Verification — end-to-end test

After all 8 phases, run this exact checklist:

1. `https://habit-coach-ai.onrender.com/admin/` → Django admin login renders with full CSS.
2. Log in with the superuser → `/admin/` dashboard shows `Users`, `Groups`.
3. Supabase dashboard → Database → SQL Editor → `SELECT count(*) FROM auth_user;` → returns ≥ 1.
4. `render logs habit-coach-ai --tail` (one request to `/admin/`) → no Python tracebacks, no 5xx.
5. Claude Code `/mcp` → `render` connected → `render.get_service('habit-coach-ai')` returns status `live`.
6. `context/deployment/deploy-plan.md` exists and mirrors this plan.
7. `git log --oneline` shows the initial commit (and any cleanup commits made during deploy).

If ANY of 1–6 fails, do not call the deploy done — investigate the corresponding phase's gate.

## Out of scope

Explicitly NOT in this plan (deferred to later work):
- Django apps (`startapp habits`, models, views, templates) — that's the next implementation phase (`/10x-implement`).
- CI/CD via GitHub Actions — `auto-deploy-on-merge` is handled natively by Render's Git integration; explicit Actions workflow comes later if needed.
- Custom domain on Render (`habit-coach.app` or similar) — uses default `onrender.com` for now.
- Production OpenRouter integration — only the key is provisioned; actual `openai`/`anthropic` SDK code is FR-011/FR-013 work.
- Monitoring/error tracking (Sentry, BetterStack) — deferred until the app has real user traffic.
- Backup automation — manual `supabase db dump > backups/pre-<commit>.sql` is a documented habit; cron-style automation comes post-MVP.

## Risk reminders (from `@context/foundation/infrastructure.md`)

- **Render free tier 60s cold start violates FR-013 NFR**. Start on Starter ($7/mo) from day one — already encoded in `render.yaml`.
- **`preDeployCommand` migration failure leaves Postgres partially migrated**. Take `supabase db dump > backups/pre-<short-sha>.sql` before any `git push` carrying a `makemigrations` artifact.
- **Render MCP token = workspace-wide**. Rotate after any sensitive session.
- **`CONN_MAX_AGE=600`** is set in `settings.py` Phase 1 refactor — keep it; this prevents connection churn under load (pre-mortem warning).
