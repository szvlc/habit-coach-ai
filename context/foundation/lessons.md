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
