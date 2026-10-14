"""The rules tying a Transaction to a Goal (Goals spec section 4, ADR-0031).

Shared by the real store and the test FakeStore, so the two cannot come to
state a rule, or its message, differently - the same arrangement as
transaction_log.categories.require_valid_type_category_pair.
"""

from goals.goal import ACTIVE, Goal

# The one Category whose Transactions are Contributions to a Goal.
GOALS_CATEGORY = "Goals"


def is_goals_category(category: str) -> bool:
    return category == GOALS_CATEGORY


def require_not_goals_category(category: str) -> None:
    """Raise ValueError if `category` is Goals: a Recurring Transactions Config
    rule there would generate Contributions with no Goal (Goals spec section 4).
    Specific to Goals, not to locked Categories in general."""
    if is_goals_category(category):
        raise ValueError(f"The {GOALS_CATEGORY} Category can't be used in a Recurring Transactions Config rule")


def require_valid_goal_link(
    category: str,
    goal_id: int | None,
    goal: Goal | None,
    current_goal_id: int | None = None,
) -> None:
    """Raise ValueError unless a Transaction in `category` may carry `goal_id`.

    `goal` is the stored Goal `goal_id` names (None when there is no such
    Goal); `current_goal_id` is the link the row being updated already has
    (None for a new row). The rules:

    1. `goal_id` is set if and only if the Category is Goals.
    2. The Goal must exist.
    3. A new link, or a move to a different Goal, needs the Goal to be active;
       a row may keep a link to a Goal that has since been archived or deleted.
    """
    if not is_goals_category(category):
        if goal_id is not None:
            raise ValueError(f"Only the {GOALS_CATEGORY} Category can be linked to a Goal")
        return

    if goal_id is None:
        raise ValueError(f"Choose a Goal for the {GOALS_CATEGORY} Category")
    if goal is None:
        raise ValueError(f"No Goal has id {goal_id}")
    if goal_id != current_goal_id and goal.state != ACTIVE:
        raise ValueError(f"Goal {goal.title!r} is not active, so it can't take new Contributions")
