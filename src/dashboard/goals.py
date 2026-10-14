"""Translation between the Goals tab's JSON shape and Goal - see the Goals
spec (docs/goals-spec.md), section 7.

Kept out of dashboard.server so the HTTP layer stays a router. The derived
figures themselves come from goals.figures; this module only puts them on the
wire.
"""

from dataclasses import asdict
from datetime import date
from decimal import Decimal

from goals.figures import describe
from goals.goal import ACTIVE, Goal, GoalDraft
from goals.links import require_valid_goal_link
from goals.split import allocate
from transaction_log.entries import Candidate

# Contributions are Savings-Type Transactions in the locked Goals Category.
CONTRIBUTION_TYPE = "Savings"
CONTRIBUTION_CATEGORY = "Goals"

# Split savings (Goals spec section 9): whatever the Goals leave of 100% is a
# Savings-Type row in one of these Categories. Its Notes differ from any
# Goal's (a Goal's rows carry its title) so the two can never collide under a
# later dedupe.
SPLIT_REMAINDER_CATEGORIES = ("Savings", "Investments")
SPLIT_REMAINDER_NOTES = "Split savings remainder"


def as_payload(goal: Goal, today: date, saved: float = 0.0) -> dict:
    """One Goal: its own fields, its lifecycle `state`, and every derived
    figure, all measured against the one `today`. `saved` is the sum of the
    Goal's linked Contributions."""
    return {
        "id": goal.id,
        "title": goal.title,
        "description": goal.description,
        "target_amount": goal.target_amount,
        "start_date": goal.start_date.isoformat(),
        "end_date": goal.end_date.isoformat(),
        "state": goal.state,
        **asdict(describe(goal, saved=saved, today=today)),
    }


def list_payload(goals: list[Goal], today: date, savings: dict[int, float] | None = None) -> dict:
    """Active Goals in `goals`, the rest in `past` (archived or deleted).
    `savings` maps a Goal id to its saved amount; a Goal not in it has none."""
    savings = savings or {}
    return {
        "today": today.isoformat(),
        "goals": [as_payload(goal, today, savings.get(goal.id, 0.0)) for goal in goals if goal.state == ACTIVE],
        "past": [as_payload(goal, today, savings.get(goal.id, 0.0)) for goal in goals if goal.state != ACTIVE],
    }


def contribution_from_payload(goal: Goal, payload) -> Candidate:
    """The Candidate an Add contribution request describes: a Goals-Category
    Savings Transaction linked to `goal`. Notes default to the Goal's title.
    Whether the Goal can take it (it must be active) is the store's call."""
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object describing one Contribution")

    missing = [field for field in ("amount", "date") if field not in payload]
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}")

    amount = payload["amount"]
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not amount > 0:
        raise ValueError("The Contribution amount must be a number above zero")

    notes = payload.get("notes")
    if notes is not None and not isinstance(notes, str):
        raise ValueError("notes must be text")

    return Candidate(
        date=_date(payload["date"], "date"),
        amount=float(amount),
        type=CONTRIBUTION_TYPE,
        category=CONTRIBUTION_CATEGORY,
        notes=(notes or "").strip() or goal.title,
        goal_id=goal.id,
    )


def split_from_payload(payload, goals: list[Goal]) -> list[Candidate]:
    """The Transactions a Split savings request would write: one Contribution
    per Goal with a non-zero share, then one remainder row unless the Goals
    take exactly 100%. The server owns the allocation (largest-remainder
    cents, goals.split); the request carries only a total and percentages.
    `goals` is every stored Goal, to find each named Goal and check it is
    active."""
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object describing one split")

    missing = [field for field in ("total", "date", "allocations", "remainder_category") if field not in payload]
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}")

    total_cents = _cents(payload["total"])
    when = _date(payload["date"], "date")

    category = payload["remainder_category"]
    if category not in SPLIT_REMAINDER_CATEGORIES:
        raise ValueError(f"The remainder must go to {' or '.join(SPLIT_REMAINDER_CATEGORIES)}")

    allocations = payload["allocations"]
    if not isinstance(allocations, list) or not all(isinstance(a, dict) for a in allocations):
        raise ValueError("allocations must be a list of { goal_id, percent }")

    stored = {goal.id: goal for goal in goals}
    chosen = []
    percents = []
    for allocation in allocations:
        goal_id = allocation.get("goal_id")
        percent = allocation.get("percent")
        if isinstance(percent, bool) or not isinstance(percent, (int, float)):
            raise ValueError("Each percent must be a number")
        goal = stored.get(goal_id)
        require_valid_goal_link(CONTRIBUTION_CATEGORY, goal_id, goal)
        if goal in chosen:
            raise ValueError(f"Goal {goal.title!r} appears more than once")
        chosen.append(goal)
        percents.append(percent)

    goal_cents, remainder_cents = allocate(total_cents, percents)

    rows = [
        Candidate(
            date=when,
            amount=cents / 100,
            type=CONTRIBUTION_TYPE,
            category=CONTRIBUTION_CATEGORY,
            notes=goal.title,
            goal_id=goal.id,
        )
        for goal, cents in zip(chosen, goal_cents)
        if cents > 0
    ]
    if remainder_cents > 0:
        rows.append(
            Candidate(
                date=when,
                amount=remainder_cents / 100,
                type=CONTRIBUTION_TYPE,
                category=category,
                notes=SPLIT_REMAINDER_NOTES,
            )
        )
    return rows


def _cents(total) -> int:
    if isinstance(total, bool) or not isinstance(total, (int, float)) or not total > 0:
        raise ValueError("The total must be a number above zero")
    cents = Decimal(str(total)) * 100
    if cents != cents.to_integral_value():
        raise ValueError("The total can't have fractions of a cent")
    return int(cents)


def draft_from_payload(payload) -> GoalDraft:
    """The GoalDraft a create or edit request body describes."""
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object describing one Goal")

    missing = [field for field in ("title", "target_amount", "start_date", "end_date") if field not in payload]
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}")

    title = payload["title"]
    if not isinstance(title, str):
        raise ValueError("title must be text")

    description = payload.get("description")
    if description is not None and not isinstance(description, str):
        raise ValueError("description must be text or null")

    target = payload["target_amount"]
    if isinstance(target, bool) or not isinstance(target, (int, float)):
        raise ValueError("target_amount must be a number")

    return GoalDraft(
        title=title.strip(),
        description=(description.strip() or None) if description is not None else None,
        target_amount=float(target),
        start_date=_date(payload["start_date"], "start_date"),
        end_date=_date(payload["end_date"], "end_date"),
    )


def _date(value, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a date (YYYY-MM-DD)") from None
