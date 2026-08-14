from typing import Callable

from statement_export.parser import RawTransaction
from transaction_log.categories import SUB_CATEGORIES_BY_CATEGORY


class TerminalReviewer:
    """Resolves a Needs Review transaction via a prompt loop in the terminal.

    Callable as (transaction, reason) -> (category, sub_category), matching
    statement_export.orchestrator.NeedsReviewResolver - the default resolver
    process_statement_export's __main__ wires in for real runs.
    """

    def __init__(
        self,
        category_list: dict[str, set[str]] = SUB_CATEGORIES_BY_CATEGORY,
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[[str], None] = print,
    ):
        self._category_list = category_list
        self._input = input_fn
        self._print = print_fn

    def __call__(self, transaction: RawTransaction, reason: str | None) -> tuple[str, str]:
        self._print(
            f"\nNeeds Review: {transaction.date.isoformat()}  {transaction.amount:.2f}  {transaction.notes}"
        )
        if reason:
            self._print(f"  ({reason})")

        categories = sorted(self._category_list)
        category = self._choose("Category", categories)
        sub_category = self._choose(f"Sub-category for {category}", sorted(self._category_list[category]))
        return category, sub_category

    def _choose(self, label: str, options: list[str]) -> str:
        while True:
            self._print(f"{label}:")
            for i, option in enumerate(options, start=1):
                self._print(f"  {i}. {option}")
            choice = self._input(f"{label} number: ").strip()
            selected = _select(choice, options)
            if selected is not None:
                return selected
            self._print("Not a valid choice, try again.")


def _select(choice: str, options: list[str]) -> str | None:
    if not choice.isdigit():
        return None
    index = int(choice) - 1
    if not (0 <= index < len(options)):
        return None
    return options[index]
