---
bootstrapped_at: 2026-05-20T22:15:00Z
starter_id: django
starter_name: Django
project_name: habit-coach-ai
language_family: python
package_manager: uv
cwd_strategy: native-cwd
bootstrapper_confidence: verified
phase_3_status: ok
audit_command: pip-audit
---

## Hand-off

Verbatim copy of `context/foundation/tech-stack.md`:

```yaml
starter_id: django
package_manager: uv
project_name: habit-coach-ai
hints:
  language_family: python
  team_size: solo
  deployment_target: fly
  ci_provider: github-actions
  ci_default_flow: auto-deploy-on-merge
  bootstrapper_confidence: verified
  path_taken: standard
  quality_override: false
  self_check_answers: null
  has_auth: true
  has_payments: false
  has_realtime: false
  has_ai: true
  has_background_jobs: false
```

### Why this stack

Solo developer building HabitCoach AI as a small after-hours web app in 3 weeks. Django is the recommended default for `(web, python)` and clears all four agent-friendly gates with the Python-family caveat. Auth, PostgreSQL, migrations, and admin ship out of the box, so FR-001..003 (email/password + reset) and the per-user isolation guardrail land with minimal scaffolding — leaving only the AI recommendation step (FR-011, FR-013) to assemble against the user's habit history. Fly is Django's first deployment default; GitHub Actions with auto-deploy-on-merge is the standard shape for solo + small-scale projects. Payments, realtime, and background jobs are out of scope per PRD non-goals; the proactive recommendation in FR-013 is modeled as a check at request time, not a scheduled job. Bootstrapper confidence is verified, so scaffolding will be smooth.

## Pre-scaffold verification

| Signal             | Value                                       | Severity | Notes                                                                 |
| ------------------ | ------------------------------------------- | -------- | --------------------------------------------------------------------- |
| npm package        | not run                                     | n/a      | non-JS starter (`hints.language_family: python`) — npm step skipped   |
| GitHub repo        | not run                                     | n/a      | card `docs_url` is `https://docs.djangoproject.com` (not a github.com URL) — no GitHub recency signal available |

No recency warning surfaced. Step 1 proceeded with no halting condition.

## Scaffold log

**Resolved invocation**: `uv init --bare && uv add django && uv run django-admin startproject habit_coach_ai .`
**Strategy**: native-cwd
**Exit code**: 0
**Pre-flight files-to-touch**: `pyproject.toml`, `uv.lock`, `.python-version`, `.venv/` (from `uv init` + `uv add`), `manage.py`, `habit_coach_ai/__init__.py`, `habit_coach_ai/settings.py`, `habit_coach_ai/urls.py`, `habit_coach_ai/wsgi.py`, `habit_coach_ai/asgi.py` (from `django-admin startproject`)
**Files written by CLI**: 10 (4 from uv, 6 from django-admin)
**Pre-existing files preserved**: `.claude/`, `CLAUDE.md`, `context/`, `idea-notes.md`, `memory/` — none touched by the scaffold; no `.scaffold` siblings created

**Adaptations from card defaults** (recorded for audit completeness):

- Card carries `pre: "pip install django"`; the hand-off picked `uv` as `package_manager`, so the pre-step was executed as `uv init --bare && uv add django` to keep the install path consistent with the user's chosen package manager. Resulting dependency graph is identical (`django==6.0.5` plus its transitive deps).
- Card `cmd_template` is `django-admin startproject {name} .`. The scaffold-merge substitution rule states `{name}` becomes `.` for `native-cwd`, but Django's CLI requires the first argument to be a valid Python identifier (no hyphens). The hand-off `project_name` is `habit-coach-ai` (kebab-case). Pragmatic interpretation: `{name}` was substituted with the snake_case-sanitized project name `habit_coach_ai`, with the literal `.` after `{name}` retained as the target-directory argument. Original kebab-case `project_name` is preserved in the hand-off and this log; the Django package name on disk is `habit_coach_ai`.

## Post-scaffold audit

**Tool**: `pip-audit --format json` (run via `uv run --with pip-audit`)
**Summary**: 0 CRITICAL, 0 HIGH, 0 MODERATE, 0 LOW
**Direct vs transitive**: not distinguished by this tool

Clean tree. `pip-audit` examined 33 packages (django + its direct deps `asgiref`, `sqlparse`, `tzdata`, plus pip-audit's own runtime tree). No advisories returned. Exit code 0.

Full dependency snapshot (audit time):

```
asgiref==3.11.1, boolean-py==5.0, cachecontrol==0.14.4, certifi==2026.5.20,
charset-normalizer==3.4.7, cyclonedx-python-lib==11.7.0, defusedxml==0.7.1,
django==6.0.5, filelock==3.29.0, idna==3.15, license-expression==30.4.4,
markdown-it-py==4.2.0, mdurl==0.1.2, msgpack==1.1.2, packageurl-python==0.17.6,
packaging==26.2, pip==26.1.1, pip-api==0.0.34, pip-audit==2.10.0,
pip-requirements-parser==32.0.1, platformdirs==4.9.6, py-serializable==2.1.0,
pygments==2.20.0, pyparsing==3.3.2, requests==2.34.2, rich==15.0.0,
sortedcontainers==2.4.0, sqlparse==0.5.5, tomli==2.4.1, tomli-w==1.2.0,
typing-extensions==4.15.0, tzdata==2026.2, urllib3==2.7.0
```

(pip-audit's own transitive tree is included because it was installed into the same uv environment; only `django`, `asgiref`, `sqlparse`, `tzdata` belong to the actual project runtime.)

## Hints recorded but not acted on

| Hint                       | Value             |
| -------------------------- | ----------------- |
| bootstrapper_confidence    | verified          |
| quality_override           | false             |
| path_taken                 | standard          |
| self_check_answers         | null              |
| team_size                  | solo              |
| deployment_target          | fly               |
| ci_provider                | github-actions    |
| ci_default_flow            | auto-deploy-on-merge |
| has_auth                   | true              |
| has_payments               | false             |
| has_realtime               | false             |
| has_ai                     | true              |
| has_background_jobs        | false             |

These were read into bootstrapper's working memory and logged here for audit completeness. v1 does not act on them — no CI workflow generated, no auth scaffolding beyond what Django ships out of the box, no AI integration boilerplate, no deployment config for Fly. The future M1L4 skill ("agent context / memory architecture") is the next link in the chain that will consume these.

## Next steps

Next: a future skill will set up agent context (CLAUDE.md, AGENTS.md). For now, your project is scaffolded and verified — happy hacking.

Useful manual steps in the meantime:

- `git init` (if you have not already) to start your own repo history.
- The scaffold did not create `.scaffold` siblings (no pre-existing scaffold-shaped files in cwd); nothing to diff.
- Run `uv run python manage.py migrate` to apply Django's initial migrations against the default SQLite dev database (swap to PostgreSQL when ready per the PRD).
- `uv run python manage.py createsuperuser` to seed an admin login for the built-in Django admin (covers FR-001..003's email-based auth out of the box).
- Audit is clean today (2026-05-20); re-run `uv run --with pip-audit pip-audit` periodically as the dep tree evolves.
