from typing import Callable

from statement_export.parser import RawTransaction
from transaction_log.categories import CATEGORIES_BY_TYPE, types_with_categories


class TerminalReviewer:
    """Resolves a Needs Review transaction via a prompt loop in the terminal.

    Callable as (transaction, reason) -> (type, category), matching
    statement_export.orchestrator.NeedsReviewResolver - the default resolver
    process_statement_export's __main__ wires in for real runs.
    """

    def __init__(
        self,
        categories_by_type: dict[str, set[str]] = CATEGORIES_BY_TYPE,
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[[str], None] = print,
    ):
        self._categories_by_type = categories_by_type
        self._input = input_fn
        self._print = print_fn

    def __call__(self, transaction: RawTransaction, reason: str | None) -> tuple[str, str]:
        self._print(
            f"\nNeeds Review: {transaction.date.isoformat()}  {transaction.amount:.2f}  {transaction.notes}"
        )
        if reason:
            self._print(f"  ({reason})")

        transaction_type = self._choose("Type", types_with_categories(self._categories_by_type))
        category = self._choose(
            f"Category for {transaction_type}", sorted(self._categories_by_type[transaction_type])
        )
        return transaction_type, category

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
