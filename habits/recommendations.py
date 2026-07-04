"""AI recommendation logic (S-04, FR-011). Pure functions + a single OpenRouter
call, decoupled from views so they are unit-testable with the LLM mocked.

Per-user isolation is load-bearing here: every function that touches data draws
ONLY from the given user's querysets (Habit.objects.active(user) /
HabitExecution.objects.history_for(user, ...)). The prompt sent to OpenRouter
never contains another user's data.
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from openai import OpenAI

from .models import Habit, HabitExecution, Recommendation

HISTORY_DAYS = 30
# Proactive recommendation (FR-013): fire after the user has logged on this many
# distinct days.
HISTORY_THRESHOLD_DAYS = 7

# Monday=0 .. Sunday=6 (matches date.weekday())
WEEKDAY_NAMES_PL = [
    "poniedziałek",
    "wtorek",
    "środa",
    "czwartek",
    "piątek",
    "sobota",
    "niedziela",
]


def longest_streak(dates):
    """Longest run of consecutive calendar days present in `dates`. 0 if empty.

    Order-independent; duplicates collapse. Counts each run once from its start
    (a day whose previous day is absent)."""
    unique = set(dates)
    best = 0
    for d in unique:
        if d - timedelta(days=1) in unique:
            continue  # not the start of a run
        length = 1
        cur = d
        while cur + timedelta(days=1) in unique:
            length += 1
            cur += timedelta(days=1)
        best = max(best, length)
    return best


def build_history_context(user):
    """Assemble grounding data for one user: active habits + 30-day signals.

    Returns {today, start, days, habits: [{name, done_count, current_streak,
    completion_rate, weakest_weekday, last_break}]}. Draws only from `user`.
    """
    today = timezone.localdate()
    start = today - timedelta(days=HISTORY_DAYS - 1)
    days = [start + timedelta(days=offset) for offset in range(HISTORY_DAYS)]
    habits = list(Habit.objects.active(user))
    done = set(
        HabitExecution.objects.history_for(user, start).values_list("habit_id", "date")
    )

    rows = []
    for habit in habits:
        done_days = [d for d in days if (habit.pk, d) in done]

        # Current streak: consecutive days up to and including today.
        streak = 0
        cursor = today
        while (habit.pk, cursor) in done:
            streak += 1
            cursor -= timedelta(days=1)

        completion_rate = round(100 * len(done_days) / HISTORY_DAYS)

        # Weakest weekday: lowest done/occurrences ratio across the window.
        totals, dones = {}, {}
        for d in days:
            wd = d.weekday()
            totals[wd] = totals.get(wd, 0) + 1
            if (habit.pk, d) in done:
                dones[wd] = dones.get(wd, 0) + 1
        ratios = {wd: dones.get(wd, 0) / totals[wd] for wd in totals}
        weakest_weekday = None
        if ratios and min(ratios.values()) < 1:
            weakest_wd = min(ratios, key=ratios.get)
            weakest_weekday = WEEKDAY_NAMES_PL[weakest_wd]

        # Most recent day without an execution.
        last_break = next((d for d in reversed(days) if (habit.pk, d) not in done), None)

        rows.append(
            {
                "name": habit.name,
                "done_count": len(done_days),
                "current_streak": streak,
                "longest_streak": longest_streak(done_days),
                "completion_rate": completion_rate,
                "weakest_weekday": weakest_weekday,
                "last_break": last_break,
            }
        )

    return {"today": today, "start": start, "days": days, "habits": rows}


def build_daily_completion(user):
    """Per-day completion over the 30-day window for one user's active habits.

    Returns a list of HISTORY_DAYS dicts [{date, done_count, total, ratio, pct}]:
    total is the count of the user's active habits, done_count how many were
    executed that day, ratio/pct the fraction (0 when total==0). Draws only from
    `user` (history_for already excludes archived habits and other users)."""
    today = timezone.localdate()
    start = today - timedelta(days=HISTORY_DAYS - 1)
    days = [start + timedelta(days=offset) for offset in range(HISTORY_DAYS)]
    total = Habit.objects.active(user).count()
    counts = {}
    for d in HabitExecution.objects.history_for(user, start).values_list("date", flat=True):
        counts[d] = counts.get(d, 0) + 1
    return [
        {
            "date": d,
            "done_count": counts.get(d, 0),
            "total": total,
            "ratio": (counts.get(d, 0) / total) if total else 0,
            "pct": round(100 * counts.get(d, 0) / total) if total else 0,
        }
        for d in days
    ]


def build_messages(context):
    """Build chat messages with an explicit grounding instruction (Polish)."""
    system = (
        "Jesteś trenerem nawyków. Na podstawie WYŁĄCZNIE poniższych danych "
        "użytkownika napisz krótką, konkretną rekomendację (2-4 zdania). Odnoś "
        "się do KONKRETNYCH nazw nawyków i ich wzorców (streak, procent "
        "ukończenia, najsłabszy dzień tygodnia, ostatnia przerwa). NIE dawaj "
        "generycznych porad typu „pij więcej wody” czy „śpij 8 godzin”. Pisz "
        "po polsku, w drugiej osobie."
    )

    lines = [f"Dane z ostatnich {HISTORY_DAYS} dni:"]
    for h in context["habits"]:
        parts = [
            f"- Nawyk „{h['name']}”: wykonany {h['done_count']}/{HISTORY_DAYS} dni "
            f"({h['completion_rate']}%), aktualny streak {h['current_streak']} dni"
        ]
        if h.get("longest_streak", 0) > 1:
            parts.append(f", najdłuższa seria: {h['longest_streak']} dni")
        if h["weakest_weekday"]:
            parts.append(f", najsłabszy dzień: {h['weakest_weekday']}")
        if h["last_break"]:
            parts.append(f", ostatnia przerwa: {h['last_break']:%Y-%m-%d}")
        lines.append("".join(parts) + ".")
    user = "\n".join(lines)

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def generate_recommendation(user):
    """Single synchronous OpenRouter call. Returns (text, model_used).

    Raises on API error / timeout — the caller (view) handles it. This is the
    one function mocked in view tests.
    """
    messages = build_messages(build_history_context(user))
    client = OpenAI(
        base_url=settings.OPENROUTER_BASE_URL,
        api_key=settings.OPENROUTER_API_KEY,
    )
    completion = client.chat.completions.create(
        model=settings.OPENROUTER_MODEL,
        messages=messages,
        max_tokens=settings.OPENROUTER_MAX_TOKENS,
        timeout=settings.OPENROUTER_TIMEOUT,
    )
    text = (completion.choices[0].message.content or "").strip()
    return text, settings.OPENROUTER_MODEL


def can_generate(user):
    """Data threshold for FR-011: at least one active habit and one logged
    execution — without history there is nothing concrete to ground on."""
    return (
        Habit.objects.active(user).exists()
        and HabitExecution.objects.filter(habit__user=user).exists()
    )


def logged_day_count(user):
    """Number of distinct dates on which the user logged an execution of an
    active habit. Excludes archived habits for parity with history_for (the
    prompt source), so the threshold counts the same data the rec is built from."""
    return (
        HabitExecution.objects.filter(habit__user=user, habit__archived=False)
        .values("date")
        .distinct()
        .count()
    )


def auto_recommendation_due(user):
    """FR-013 one-time proactive trigger: threshold reached AND no proactive
    recommendation generated yet. Persisting only on success keeps this True
    after a silent failure, so it retries on the next dashboard load."""
    return (
        not Recommendation.objects.filter(user=user, proactive=True).exists()
        and logged_day_count(user) >= HISTORY_THRESHOLD_DAYS
    )


def is_grounded(text, user):
    """Observational Q2 token-check: does the text reference concrete user data?

    True when the text mentions at least one of the user's active habit names
    (case-insensitive). Observability only — never gates output.
    """
    lowered = text.lower()
    names = Habit.objects.active(user).values_list("name", flat=True)
    return any(name.lower() in lowered for name in names)
