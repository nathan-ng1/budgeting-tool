# Every Category has exactly one fixed Type — see CONTEXT.md and ADR-0006. Transfer
# starts empty on purpose: its Categories are added lazily, only for real cases.
CATEGORIES_BY_TYPE = {
    "Income": {
        "Salary",
        "Beem Adjustment",
        "Rental",
        "Refund",
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
        "Mortgage Repayment",
    },
    "Transfer": set(),
}


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


def types_with_categories(categories_by_type: dict[str, set[str]] = CATEGORIES_BY_TYPE) -> list[str]:
    """The Types that can actually be assigned, sorted.

    A Type with no Categories yet (Transfer) is left out: nothing downstream
    can produce a valid (Type, Category) pair for it, so neither the
    categorisation prompt nor the Needs Review prompt should offer it.
    """
    return sorted(t for t, categories in categories_by_type.items() if categories)
