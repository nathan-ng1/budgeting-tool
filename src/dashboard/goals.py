"""Translation between the Goals tab's JSON shape and Goal - see the Goals
spec (docs/goals-spec.md), section 7.

Kept out of dashboard.server so the HTTP layer stays a router. The derived
figures themselves come from goals.figures; this module only puts them on the
wire.
"""

from dataclasses import asdict
from datetime import date

from goals.figures import describe
from goals.goal import ACTIVE, Contribution, Goal, GoalDraft
from transaction_log.entries import Candidate

# Contributions are Savings-Type Transactions in the locked Goals Category.
CONTRIBUTION_TYPE = "Savings"
CONTRIBUTION_CATEGORY = "Goals"


def as_payload(goal: Goal, today: date, saved: float = 0.0, contributions: list[Contribution] | None = None) -> dict:
    """One Goal: its own fields, its lifecycle `state`, and every derived
    figure, all measured against the one `today`. `saved` is the sum of the
    Goal's linked Contributions and `contributions` is their ledger, oldest
    first, for the Details view."""
    return {
        "id": goal.id,
        "title": goal.title,
        "description": goal.description,
        "target_amount": goal.target_amount,
        "start_date": goal.start_date.isoformat(),
        "end_date": goal.end_date.isoformat(),
        "state": goal.state,
        **asdict(describe(goal, saved=saved, today=today)),
        "contributions": [
            {"date": c.date.isoformat(), "notes": c.notes, "amount": c.amount} for c in contributions or []
        ],
    }


def list_payload(
    goals: list[Goal],
    today: date,
    savings: dict[int, float] | None = None,
    ledgers: dict[int, list[Contribution]] | None = None,
) -> dict:
    """Active Goals in `goals`, the rest in `past` (archived or deleted).
    `savings` maps a Goal id to its saved amount and `ledgers` to its
    Contributions; a Goal not in either has none."""
    savings = savings or {}
    ledgers = ledgers or {}
    return {
        "today": today.isoformat(),
        "goals": [as_payload(goal, today, savings.get(goal.id, 0.0), ledgers.get(goal.id)) for goal in goals if goal.state == ACTIVE],
        "past": [as_payload(goal, today, savings.get(goal.id, 0.0), ledgers.get(goal.id)) for goal in goals if goal.state != ACTIVE],
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
