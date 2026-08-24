from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Candidate:
    date: date
    amount: float
    type: str
    category: str
    notes: str

    def __post_init__(self):
        # The (Type, Category) pair is validated by whichever store call ends
        # up persisting this Candidate, not here - Category is user-editable,
        # per-instance data (Issue #91), so only the live `categories` table
        # can say whether a pair is valid. Mirrors RecurringRule, which has
        # never validated its own pair for the same reason.
        if self.amount == 0:
            raise ValueError("Amount can't be zero")

    @property
    def stored_amount(self) -> float:
        """Amount as written to the Transaction Log - always positive except
        Category Beem Adjustment, a deliberate, narrow exception (ADR-0015)
        that stores negative so it reduces Expense totals instead of adding
        to them.
        """
        if self.category == "Beem Adjustment":
            return self.amount
        return abs(self.amount)


@dataclass(frozen=True)
class ExistingRow:
    date: date
    amount: float
    notes: str


@dataclass(frozen=True)
class Transaction:
    id: int
    date: date
    amount: float
    type: str
    category: str
    notes: str


@dataclass(frozen=True)
class WriteResult:
    to_write: list[Candidate]
    skipped: list[Candidate]
