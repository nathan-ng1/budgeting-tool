from dataclasses import dataclass
from datetime import date

from transaction_log.categories import is_valid_type_category_pair


@dataclass(frozen=True)
class Candidate:
    date: date
    amount: float
    type: str
    category: str
    notes: str

    def __post_init__(self):
        if self.amount == 0:
            raise ValueError("Amount can't be zero")
        if not is_valid_type_category_pair(self.type, self.category):
            raise ValueError(
                f"Category {self.category!r} is not valid for Type {self.type!r}"
            )

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
