"""A Goal: a savings target with a required end date (GLOSSARY "Goal",
ADR-0031). Only what the user typed and the lifecycle state are stored;
Status, saved amount, pace and the monthly figures are derived (see
goals.figures), never persisted.
"""

from dataclasses import dataclass
from datetime import date

ACTIVE = "active"
ARCHIVED = "archived"
DELETED = "deleted"
STATES = (ACTIVE, ARCHIVED, DELETED)


class GoalNotFound(LookupError):
    """No Goal has the given id."""


@dataclass(frozen=True)
class GoalDraft:
    """What a create or edit request describes, validated on construction.

    Title uniqueness needs the other Goals, so the store checks that; the
    rules that depend on the draft alone live here.
    """

    title: str
    description: str | None
    target_amount: float
    start_date: date
    end_date: date

    def __post_init__(self):
        if not self.title:
            raise ValueError("Give the Goal a title")
        if not self.target_amount > 0:
            raise ValueError("The target amount must be above zero")
        if self.end_date < self.start_date:
            raise ValueError("The end date can't be before the start date")


@dataclass(frozen=True)
class Goal:
    id: int
    title: str
    description: str | None
    target_amount: float
    start_date: date
    end_date: date
    state: str


@dataclass(frozen=True)
class Contribution:
    """One line of a Goal's Contributions ledger: the linked Transaction's date,
    notes and amount. The Transaction itself is edited on the Transactions tab."""

    date: date
    notes: str
    amount: float
