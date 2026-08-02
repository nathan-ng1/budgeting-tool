from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Candidate:
    date: date
    amount: float
    category: str
    sub_category: str
    notes: str


@dataclass(frozen=True)
class LoggedTransaction:
    date: date
    amount: float
    notes: str


@dataclass(frozen=True)
class WriteResult:
    to_write: list[Candidate]
    skipped: list[Candidate]
