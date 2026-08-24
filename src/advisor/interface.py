from dataclasses import dataclass
from typing import Protocol


class MalformedResponseError(Exception):
    """A backend's response didn't produce a usable write-up."""


@dataclass(frozen=True)
class CategoryHistory:
    """One Expense or Debt Category's recent Budgeted-vs-Actual history, the
    same shape dashboard.queries.get_budget_editor already computes for the
    Budget tab's grey historical columns (Issue #63) - reused here rather
    than recomputed, per Issue #65's "Blocked by" note.
    """

    type: str
    category: str
    last_month_actual: float
    last_month_budgeted: float | None
    trailing_average_actual: float | None
    average_variance_pct: float | None


@dataclass(frozen=True)
class SuggestionResult:
    write_up: str


class Advisor(Protocol):
    def advise(self, history: list[CategoryHistory]) -> SuggestionResult: ...
