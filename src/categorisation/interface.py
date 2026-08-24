from dataclasses import dataclass
from typing import Protocol

from statement_export.parser import RawTransaction
from transaction_log.categories import Category


class MalformedResponseError(Exception):
    """A backend's response didn't match the expected structured contract."""


@dataclass(frozen=True)
class CategoryResult:
    type: str | None
    category: str | None
    needs_review: bool
    reason: str | None = None


@dataclass(frozen=True)
class BatchResult:
    results: list[CategoryResult]


class Categoriser(Protocol):
    def categorise(
        self,
        transactions: list[RawTransaction],
        categories: list[Category],
    ) -> BatchResult: ...
