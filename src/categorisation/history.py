"""The Transaction Log as categorisation memory (ADR-0026).

Two pure operations over Transaction Log rows: split_history_matches picks
out the card Transactions whose Notes have only ever had one (Type, Category)
- History Matches, which skip the backend and Needs Review entirely - and
prompt_examples picks the past Notes -> Category pairs the backend is shown
as hints for everything else. Neither does any I/O: the caller reads the
rows once per file and passes them in.
"""

import re
from dataclasses import dataclass
from datetime import date

from statement_export.parser import RawTransaction
from transaction_log.categories import Category, assignable_categories_by_type, types_with_categories
from transaction_log.entries import Candidate, Transaction

# How many normalised Notes keys the prompt examples carry - the most
# recently seen first. Kept small enough for small-context local backends.
MAX_EXAMPLES = 200

_DIGITS = re.compile(r"\d")
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Example:
    """One normalised Notes key and every (Type, Category) it has had - more
    than one pair means its rows disagree."""

    notes_key: str
    pairs: tuple[tuple[str, str], ...]


def normalise_notes(notes: str) -> str:
    """Lowercase, strip every digit, collapse whitespace, trim - so store
    numbers, terminal IDs, case and spacing don't defeat the lookup."""
    return _WHITESPACE.sub(" ", _DIGITS.sub("", notes.lower())).strip()


def split_history_matches(
    transactions: list[RawTransaction],
    history: list[Transaction],
    categories: list[Category],
) -> tuple[list[Candidate], list[RawTransaction]]:
    """Splits `transactions` into (History Matches as Candidates, the rest).

    A Transaction is a History Match only when every history row with its
    normalised Notes agrees on one (Type, Category), and that pair is one the
    backend could assign today - so never Savings (manual-entry only,
    ADR-0022). Any disagreement, ever, and it isn't.
    """
    pairs_by_key = _pairs_by_key(history, categories)
    assignable_pairs = _assignable_pairs(categories)

    matches = []
    rest = []
    for transaction in transactions:
        pairs = pairs_by_key.get(normalise_notes(transaction.notes), set())
        if len(pairs) == 1 and next(iter(pairs)) in assignable_pairs:
            transaction_type, category = next(iter(pairs))
            matches.append(
                Candidate(
                    date=transaction.date,
                    amount=transaction.amount,
                    type=transaction_type,
                    category=category,
                    notes=transaction.notes,
                )
            )
        else:
            rest.append(transaction)
    return matches, rest


def prompt_examples(
    history: list[Transaction], categories: list[Category], limit: int = MAX_EXAMPLES
) -> list[Example]:
    """The `limit` most recently seen normalised Notes keys (by latest Date),
    newest first, each with every (Type, Category) it has had."""
    pairs_by_key = _pairs_by_key(history, categories)
    latest_by_key: dict[str, date] = {}
    for row in _learnable(history, categories):
        key = normalise_notes(row.notes)
        latest_by_key[key] = max(row.date, latest_by_key.get(key, row.date))

    keys = sorted(latest_by_key, key=lambda k: (latest_by_key[k], k), reverse=True)[:limit]
    return [Example(notes_key=key, pairs=tuple(sorted(pairs_by_key[key]))) for key in keys]


def _pairs_by_key(history: list[Transaction], categories: list[Category]) -> dict[str, set[tuple[str, str]]]:
    pairs_by_key: dict[str, set[tuple[str, str]]] = {}
    for row in _learnable(history, categories):
        pairs_by_key.setdefault(normalise_notes(row.notes), set()).add((row.type, row.category))
    return pairs_by_key


def _assignable_pairs(categories: list[Category]) -> set[tuple[str, str]]:
    assignable = assignable_categories_by_type(categories)
    return {(t, name) for t in types_with_categories(assignable) for name in assignable[t]}


def _learnable(history: list[Transaction], categories: list[Category]) -> list[Transaction]:
    """History rows worth learning from: a non-empty key (Notes of only
    digits/spaces would all match each other), and not in a locked Category -
    Beem Adjustment today, whose Category is forced by direction (ADR-0015)
    and so says nothing about what the money was spent on. Driven by the
    generic `locked` column, as assignable_categories_by_type is.
    """
    locked = {c.name for c in categories if c.locked}
    return [row for row in history if row.category not in locked and normalise_notes(row.notes)]
