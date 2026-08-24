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


def assignable_categories_by_type(
    categories_by_type: dict[str, set[str]] = CATEGORIES_BY_TYPE,
) -> dict[str, set[str]]:
    """The categories-by-type view offered to the categorisation prompt.

    Beem Adjustment is excluded (see ADR-0015): it must only ever be produced
    by the deterministic Beem parser path, never model-assigned to an
    ordinary card transaction. It remains a fully valid Expense Category
    everywhere else - this only narrows what the prompt is offered.
    """
    return {
        transaction_type: categories - {"Beem Adjustment"}
        for transaction_type, categories in categories_by_type.items()
    }
