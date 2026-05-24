---
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
---

## Why this stack

Solo developer building HabitCoach AI as a small after-hours web app in 3 weeks. Django is the recommended default for `(web, python)` and clears all four agent-friendly gates with the Python-family caveat. Auth, PostgreSQL, migrations, and admin ship out of the box, so FR-001..003 (email/password + reset) and the per-user isolation guardrail land with minimal scaffolding — leaving only the AI recommendation step (FR-011, FR-013) to assemble against the user's habit history. Fly is Django's first deployment default; GitHub Actions with auto-deploy-on-merge is the standard shape for solo + small-scale projects. Payments, realtime, and background jobs are out of scope per PRD non-goals; the proactive recommendation in FR-013 is modeled as a check at request time, not a scheduled job. Bootstrapper confidence is verified, so scaffolding will be smooth.
