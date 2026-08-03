SUB_CATEGORIES_BY_CATEGORY = {
    "Bills & Subscriptions": {
        "Donations & Giving",
        "Subscriptions",
        "Insurance & Bills",
        "Rental Expense",
    },
    "Expenses": {
        "Groceries",
        "Dining & Takeaway",
        "Transport",
        "Shopping & Retail",
        "Holidays & Travel",
        "Entertainment & Leisure",
        "Health & Medical",
    },
    "Income": {"Salary", "Rental", "Beem Adjustment"},
    "Debt": {"Mortgage Repayment"},
}


def is_valid_category_pair(category: str, sub_category: str) -> bool:
    return sub_category in SUB_CATEGORIES_BY_CATEGORY.get(category, set())
