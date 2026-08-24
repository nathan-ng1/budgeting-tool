from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    """A row of the `categories` table (Issue #90) - the DB-backed source for
    what CATEGORIES_BY_TYPE used to hardcode. `type` is one of the four fixed
    Types; `locked` marks a Category (Beem Adjustment today) that the
    categorisation backend must never assign and Category Management (#91)
    must never let a user rename or delete.
    """

    id: int
    type: str
    name: str
    emoji: str | None
    locked: bool


# Every Category has exactly one fixed Type — see CONTEXT.md and ADR-0006. Transfer
# starts empty on purpose: its Categories are added lazily, only for real cases.
CATEGORIES_BY_TYPE = {
    "Income": {
        "Salary",
        "Rental",
    },
    "Expense": {
        "Groceries",
        "Dining & Takeaway",
        "Transport",
        "Shopping & Retail",
        "Holidays & Travel",
        "Entertainment & Leisure",
        "Health & Medical",
        "Donations & Giving",
        "Subscriptions",
        "Insurance & Bills",
        "Rental Expense",
        "Beem Adjustment",
    },
    "Debt": {
        "Mortgage Repayment",
    },
    "Transfer": set(),
}

# The Type order presented to a user - CONTEXT.md's own definition order, not
# the alphabetical order types_with_categories() returns below (that order is
# only for internal iteration - the categorisation prompt and terminal review -
# where display order doesn't matter).
TYPE_ORDER = ("Income", "Expense", "Debt", "Transfer")


def is_valid_type_category_pair(transaction_type: str, category: str) -> bool:
    return category in CATEGORIES_BY_TYPE.get(transaction_type, set())


def require_valid_type_category_pair(transaction_type: str, category: str) -> None:
    """Raise unless the pair is one this project allows.

    Every write path that accepts a (Type, Category) pair from outside shares
    this, so the store and its test fake can't come to state the rule - or its
    message - differently.
    """
    if not is_valid_type_category_pair(transaction_type, category):
        raise ValueError(f"Category {category!r} is not a valid {transaction_type} Category")


def type_for_category(category: str) -> str | None:
    """The Type that owns `category`, or None if it isn't a valid Category.

    The reverse of CATEGORIES_BY_TYPE - every Category has exactly one Type
    (CONTEXT.md), so this is a lookup, not a computation.
    """
    for transaction_type, categories in CATEGORIES_BY_TYPE.items():
        if category in categories:
            return transaction_type
    return None


def types_with_categories(categories_by_type: dict[str, set[str]] = CATEGORIES_BY_TYPE) -> list[str]:
    """The Types that can actually be assigned, sorted.

    A Type with no Categories yet (Transfer) is left out: nothing downstream
    can produce a valid (Type, Category) pair for it, so neither the
    categorisation prompt nor the Needs Review prompt should offer it.
    """
    return sorted(t for t, categories in categories_by_type.items() if categories)


def categories_by_type(categories: list[Category]) -> dict[str, set[str]]:
    """Every Category name grouped by its Type, from the live `categories`
    table - the DB-backed replacement for CATEGORIES_BY_TYPE wherever a
    caller already has a live `categories` list (Issue #90's dashboard query
    and API call sites). Unlike assignable_categories_by_type, this includes
    locked Categories: this is for display/lookup, not for what the
    categorisation prompt may assign.
    """
    result: dict[str, set[str]] = {}
    for category in categories:
        result.setdefault(category.type, set()).add(category.name)
    return result


def type_lookup(categories: list[Category]) -> dict[str, str]:
    """Category name -> Type, from the live `categories` table - the
    DB-backed replacement for type_for_category wherever a caller already
    has a live `categories` list, built once for O(1) lookups across many
    Categories rather than rescanning per lookup.
    """
    return {category.name: category.type for category in categories}


def assignable_categories_by_type(categories: list[Category]) -> dict[str, set[str]]:
    """The categories-by-type view offered to the categorisation prompt.

    Every locked Category (Beem Adjustment today - see ADR-0015) is excluded:
    it must only ever be produced by the deterministic Beem parser path,
    never model-assigned to an ordinary card transaction. It remains a fully
    valid Expense Category everywhere else - this only narrows what the
    prompt is offered. Driven by the generic `locked` column rather than a
    hardcoded name, so a future locked Category needs no change here.
    """
    result: dict[str, set[str]] = {}
    for category in categories:
        result.setdefault(category.type, set())
        if not category.locked:
            result[category.type].add(category.name)
    return result
