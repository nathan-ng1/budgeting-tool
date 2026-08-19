from dataclasses import dataclass
from typing import Protocol

from statement_export.parser import RawTransaction


class MalformedResponseError(Exception):
    """A backend's response didn't match the expected structured contract."""


@dataclass(frozen=True)
class CategoryResult:
    # type/category are None when is_bill_payment is True — a Bill Payment is
    # dropped, never assigned a Type/Category. See ADR-0007.
    type: str | None
    category: str | None
    needs_review: bool
    reason: str | None = None
    is_bill_payment: bool = False


@dataclass(frozen=True)
class BatchResult:
    results: list[CategoryResult]


class Categoriser(Protocol):
    def categorise(
        self,
        transactions: list[RawTransaction],
        categories_by_type: dict[str, set[str]],
    ) -> BatchResult: ...
