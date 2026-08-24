from dataclasses import dataclass
from typing import Protocol

from statement_export.parser import RawTransaction


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
        categories_by_type: dict[str, set[str]],
    ) -> BatchResult: ...
