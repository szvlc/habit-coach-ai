<!-- IMPL-REVIEW-REPORT -->
# Implementation Review (retro): Register and login

- **Plan**: `context/archive/2026-06-04-register-and-login/plan.md` (archived)
- **Scope**: All 4 phases (post-archive retro)
- **Date**: 2026-06-07
- **Verdict**: NEEDS ATTENTION
- **Findings**: 1 critical · 3 warnings · 3 observations

> Retro mode: the plan is archived and immutable. This report is written under
> a new change folder (`register-and-login-retro/`) so that follow-up work
> remains traceable without touching the archive.

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | FAIL |
| Architecture | WARNING |
| Pattern Consistency | WARNING |
| Success Criteria | WARNING |

## Findings

### F1 — Production session/CSRF hardening missing

- **Severity**: ❌ CRITICAL
- **Impact**: 🔬 HIGH — architectural stakes; think carefully before deciding
- **Dimension**: Safety & Quality
- **Location**: `habit_coach_ai/settings.py:141-148` (missing fields)
- **Detail**:
  `SESSION_COOKIE_AGE = 30 * 24 * 60 * 60` is set, but `SESSION_COOKIE_SECURE`,
  `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`,
  `SECURE_PROXY_SSL_HEADER`, and `CSRF_TRUSTED_ORIGINS` are all unset.
  Django's defaults leave each as `False` / empty. Render terminates TLS at
  the proxy, so without `SECURE_PROXY_SSL_HEADER` Django thinks every request
  is HTTP and `secure_required` machinery silently degrades. The 30-day
  session cookie is the asset being protected — without `Secure`, it can leak
  to any plaintext network the client touches. Independently verified now by
  `manage.py check --deploy` (5 warnings: W004, W008, W009, W012, W016).
- **Fix A ⭐ Recommended**: Add prod hardening block to `settings.py` gated on `not DEBUG`
  - Strength: Single-file change, idiomatic Django, addresses 4 of the 5
    `--deploy` warnings at once. Pattern matches Render's deployment guide
    (https://render.com/docs/deploy-django).
  - Tradeoff: Requires also setting `CSRF_TRUSTED_ORIGINS` (otherwise login
    POSTs break once `CSRF_COOKIE_SECURE=True`). Couples local-dev and prod
    behavior through `DEBUG`.
  - Confidence: HIGH — standard pattern; the failing `--deploy` check is the
    canonical signal.
  - Blind spot: Whether Render's exact `X-Forwarded-Proto` header name matches
    the default `("HTTP_X_FORWARDED_PROTO", "https")` — should be confirmed
    with one prod test request after deploy.
- **Fix B**: Set the flags unconditionally (no `DEBUG` gating)
  - Strength: Simpler, no dual code path; matches "production parity" instinct.
  - Tradeoff: Breaks local `runserver` over plain HTTP — login cookie won't be
    sent back, so dev login appears to silently fail.
  - Confidence: MEDIUM — works only if you also run local dev under HTTPS.
  - Blind spot: Hides the gating concern instead of making it explicit.
- **Decision**: FIXED via Fix A — added hardening block to
  `habit_coach_ai/settings.py` (gated on `not DEBUG`). Follow-up: `SECURE_SSL_REDIRECT=True`
  in tests caused 6 × 301; added `@override_settings(SECURE_SSL_REDIRECT=False)`
  to all 3 test classes in `accounts/tests.py`. `check --deploy` now emits
  2 warnings (W005, W021 — opt-in HSTS preload, intentionally not enabled).
  Tests green. Remaining action item for the user: set
  `CSRF_TRUSTED_ORIGINS=https://habit-coach-ai.onrender.com` in Render env vars.

### F2 — Phase 4 success criterion checked despite `check --deploy` warnings

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Success Criteria
- **Location**: `context/archive/2026-06-04-register-and-login/plan.md:296`
- **Detail**:
  Plan §Phase 4 / Automated #4.2 says
  `manage.py check --deploy — brak critical warnings` and is marked `[x] — d3419ba`.
  Re-running today emits 5 warnings (W004, W008, W009, W012, W016), 4 of which
  are real (the 5th is W009/SECRET_KEY length, which probably *was* fine in
  prod where the env var is long). Either (a) the box was signed on blind,
  or (b) "critical" was interpreted as "blocking" rather than literally
  matching `--deploy`'s output. Either way the success criterion didn't catch
  F1. Connects to the broader rule: a success criterion is only as strong as
  whether someone actually read its output.
- **Fix**: Treat any `--deploy` warning as a Phase 4 gate failure by default;
  if a warning is consciously accepted, annotate the progress checkbox with
  "(accepted: <why>)" rather than silently marking `[x]`.
- **Decision**: ACCEPTED-AS-RULE (lesson: "Success-criteria sign-off must
  actually read the command output", `context/foundation/lessons.md`).
  The Phase 4 criterion at `plan.md:296` was the false-OK; plan is archived
  and immutable, so the rule applies forward.

### F3 — Custom UserManager was missing from plan; added late in Phase 4

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence (EXTRA)
- **Location**: `accounts/models.py` (UserManager added);
  `accounts/migrations/0002_alter_user_managers.py` (auto-generated follow-up)
- **Detail**:
  Plan §Phase 1 §"Kluczowe odkrycia" warned about `CustomUserAdmin` being
  needed for a `USERNAME_FIELD='email'` model but stopped there. Django's
  default `UserManager.create_user(username, email=None, ...)` signature
  breaks both `manage.py createsuperuser` and the test suite's
  `User.objects.create_user(email=..., password=...)` calls
  (`accounts/tests.py:22, 43`). Discovery happened during Phase 4 test
  authoring, surfaced via commit `d3419ba feat(register-and-login):
  UserManager + 6 tests + 0002 migration (p4 local)`. The fix is correct;
  the gap is in the plan's coverage of the "custom User triplet" pattern
  (Model + Manager + Admin must all change together).
- **Fix**: Capture as a recurring rule via `/10x-lesson`:
  *"Custom User with `USERNAME_FIELD='email'` requires a custom Manager AND
  a custom Admin — they come as a triplet. Plan/research must list all three."*
  No code change needed (already fixed).
- **Decision**: SKIPPED

### F4 — Dashboard template placed at project root, not under `templates/accounts/`

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Architecture / Pattern Consistency
- **Location**: `templates/dashboard.html` (vs. expected `templates/accounts/dashboard.html`)
- **Detail**:
  `templates/registration/login.html` and `register.html` live under their
  Django-mandated `registration/` namespace, but `dashboard.html` sits flat
  at `templates/dashboard.html`. This is the first project app, so the
  choice made now becomes the convention for S-02 (habits), S-03 (logging),
  S-04 (AI rec). Flat layout will collide once habits introduces its own
  `dashboard.html`-like template. Cheap to fix now (1 file move + 1 line in
  `DashboardView`), costly after three apps share the root.
- **Fix A ⭐ Recommended**: Move `templates/dashboard.html` →
  `templates/accounts/dashboard.html`; update
  `DashboardView.template_name = "accounts/dashboard.html"`
  - Strength: Sets the per-app template namespace convention before more apps
    arrive. Idiomatic Django.
  - Tradeoff: One-line view change + one git rename.
  - Confidence: HIGH — established Django convention.
  - Blind spot: None significant; S-01 has only one view consuming this.
- **Fix B**: Leave as-is; document the flat convention explicitly in `CLAUDE.md`
  - Strength: Zero risk; no rename in git history.
  - Tradeoff: Punts the collision; future apps will need root-level template
    name prefixes (`habits_dashboard.html`) which is uglier.
  - Confidence: MEDIUM — works but trades short-term ease for long-term churn.
  - Blind spot: How many root-level templates other apps will actually need.
- **Decision**: FIXED via Fix A — `git mv templates/dashboard.html
  templates/accounts/dashboard.html`; `DashboardView.template_name` updated
  to `"accounts/dashboard.html"`. Tests green.

### F5 — Tailwind CDN script in `<head>` (3rd-party runtime dependency)

- **Severity**: 🔎 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: `templates/base.html:7`
- **Detail**:
  `<script src="https://cdn.tailwindcss.com">` runs third-party JS on every
  render (login + register included). No SRI hash possible for the JIT CDN.
  A CDN compromise = full XSS on auth pages. Accepted per tech-stack
  decisions for MVP; flag for the pre-launch hardening sweep.
- **Fix**: Track as a roadmap item — compile Tailwind to a static asset via
  the build, serve through WhiteNoise, add a basic CSP header. No action now.
- **Decision**: SKIPPED — defer to pre-launch hardening sweep.

### F6 — `AccountsConfig.default_auto_field` missing

- **Severity**: 🔎 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: `accounts/apps.py:4-5`
- **Detail**:
  Project sets `DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'`
  globally, so this is functionally redundant. But `manage.py startapp`
  always emits the field on AppConfig — its absence here is the only
  visible deviation from the boilerplate Django scaffold and may confuse
  agents that grep `default_auto_field` to verify app shape.
- **Fix**: Add `default_auto_field = 'django.db.models.BigAutoField'` to
  `AccountsConfig`.
- **Decision**: SKIPPED

### F7 — Dashboard "Add habit" CTA is `href="#"` no-op

- **Severity**: 🔎 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: `templates/dashboard.html:14`
- **Detail**:
  Honest placeholder with a TODO comment for S-02, but `href="#"` triggers a
  scroll-to-top on click, which is misleading UX for anyone who registers
  between now and S-02 shipping. Cosmetic.
- **Fix**: Render the CTA as a disabled `<span>` (muted styling) until
  `habits` app exists; swap to `<a href="{% url 'habits:add' %}">` in S-02.
- **Decision**: SKIPPED — S-02 ships next; live with the brief no-op.
