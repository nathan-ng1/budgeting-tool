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


@dataclass(frozen=True)
class ExistingRow:
    date: date
    amount: float
    notes: str


@dataclass(frozen=True)
class Transaction:
    date: date
    amount: float
    type: str
    category: str
    notes: str


@dataclass(frozen=True)
class WriteResult:
    to_write: list[Candidate]
    skipped: list[Candidate]
