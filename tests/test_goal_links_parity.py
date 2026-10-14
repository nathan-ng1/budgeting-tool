"""The Goal-link rules (Goals spec section 4), run against both the real
LocalStore and the test FakeStore, so the fake cannot drift from the store."""

from datetime import date
from pathlib import Path

import pytest

from database.store import LocalStore, connect
from goals.goal import ACTIVE, ARCHIVED, Goal, GoalDraft
from transaction_log.entries import Candidate

ACTIVE_GOAL = 1
ARCHIVED_GOAL = 2


def goal(goal_id: int, title: str, state: str) -> Goal:
    return Goal(
        id=goal_id,
        title=title,
        description=None,
        target_amount=1000.0,
        start_date=date(2026, 7, 1),
        end_date=date(2027, 6, 30),
        state=state,
    )


def local_store(tmp_path: Path) -> LocalStore:
    store = connect(tmp_path / "budget.db")
    for title in ("Japan", "Old car"):
        store.create_goal(
            GoalDraft(
                title=title,
                description=None,
                target_amount=1000.0,
                start_date=date(2026, 7, 1),
                end_date=date(2027, 6, 30),
            )
        )
    store._connection.execute("UPDATE goals SET state = 'archived' WHERE id = 2")
    store._connection.commit()
    return store


@pytest.fixture(params=["local", "fake"])
def store(request, tmp_path: Path, fake_store):
    if request.param == "local":
        return local_store(tmp_path)
    return fake_store(goals=[goal(1, "Japan", ACTIVE), goal(2, "Old car", ARCHIVED)])


def contribution(goal_id, **overrides) -> Candidate:
    fields = dict(
        date=date(2026, 10, 1),
        amount=100.0,
        type="Savings",
        category="Goals",
        notes="Top-up",
        goal_id=goal_id,
    )
    return Candidate(**{**fields, **overrides})


def test_a_goals_row_needs_a_goal(store):
    with pytest.raises(ValueError, match="Goal"):
        store.create_transaction(contribution(None))


def test_a_goal_link_on_another_category_is_rejected(store):
    with pytest.raises(ValueError):
        store.create_transaction(contribution(ACTIVE_GOAL, category="Savings"))


def test_a_missing_goal_is_rejected(store):
    with pytest.raises(ValueError, match="999"):
        store.create_transaction(contribution(999))


def test_a_new_link_to_an_inactive_goal_is_rejected(store):
    with pytest.raises(ValueError, match="active"):
        store.create_transaction(contribution(ARCHIVED_GOAL))


def test_a_linked_row_is_read_back_with_its_goal_and_counts_as_saved(store):
    created = store.create_transaction(contribution(ACTIVE_GOAL))

    assert created.goal_id == ACTIVE_GOAL
    assert [(t.goal_id, t.goal_title) for t in store.read_transactions()] == [(ACTIVE_GOAL, "Japan")]
    assert store.read_goal_savings() == {ACTIVE_GOAL: 100.0}


def test_moving_a_row_onto_an_inactive_goal_is_a_new_link_and_rejected(store):
    created = store.create_transaction(contribution(ACTIVE_GOAL))

    with pytest.raises(ValueError, match="active"):
        store.update_transaction(created.id, contribution(ARCHIVED_GOAL))


def test_a_row_must_drop_its_link_to_leave_the_goals_category(store):
    created = store.create_transaction(contribution(ACTIVE_GOAL))

    with pytest.raises(ValueError):
        store.update_transaction(created.id, contribution(ACTIVE_GOAL, category="Savings"))

    updated = store.update_transaction(created.id, contribution(None, category="Savings"))
    assert updated.goal_id is None


def test_a_written_row_comes_back_with_its_goal_title_and_state(store):
    created = store.create_transaction(contribution(ACTIVE_GOAL))
    assert (created.goal_title, created.goal_state) == ("Japan", ACTIVE)

    updated = store.update_transaction(created.id, contribution(ACTIVE_GOAL, amount=50.0))
    assert (updated.goal_title, updated.goal_state) == ("Japan", ACTIVE)

    unlinked = store.update_transaction(created.id, contribution(None, category="Savings"))
    assert (unlinked.goal_title, unlinked.goal_state) == (None, None)


def test_a_row_keeps_showing_its_goal_after_the_goal_is_archived(store):
    created = store.create_transaction(contribution(ACTIVE_GOAL))
    if isinstance(store, LocalStore):
        store._connection.execute("UPDATE goals SET state = 'archived' WHERE id = 1")
        store._connection.commit()
    else:
        store._goals[0] = goal(1, "Japan", ARCHIVED)

    [row] = store.read_transactions()
    assert (row.id, row.goal_title, row.goal_state) == (created.id, "Japan", ARCHIVED)

