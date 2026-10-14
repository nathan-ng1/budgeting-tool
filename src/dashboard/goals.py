"""Translation between the Goals tab's JSON shape and Goal - see the Goals
spec (docs/goals-spec.md), section 7.

Kept out of dashboard.server so the HTTP layer stays a router. The derived
figures themselves come from goals.figures; this module only puts them on the
wire.
"""

from dataclasses import asdict
from datetime import date

from goals.figures import describe
from goals.goal import ACTIVE, Goal, GoalDraft


def as_payload(goal: Goal, today: date) -> dict:
    """One Goal: its own fields, its lifecycle `state`, and every derived
    figure, all measured against the one `today`."""
    return {
        "id": goal.id,
        "title": goal.title,
        "description": goal.description,
        "target_amount": goal.target_amount,
        "start_date": goal.start_date.isoformat(),
        "end_date": goal.end_date.isoformat(),
        "state": goal.state,
        **asdict(describe(goal, saved=0.0, today=today)),
    }


def list_payload(goals: list[Goal], today: date) -> dict:
    """Active Goals in `goals`, the rest in `past` (archived or deleted)."""
    return {
        "today": today.isoformat(),
        "goals": [as_payload(goal, today) for goal in goals if goal.state == ACTIVE],
        "past": [as_payload(goal, today) for goal in goals if goal.state != ACTIVE],
    }


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
