# The old six-Category model's remap to the new Type/Category model — see ADR-0005
# and ADR-0006. Verified mechanical against the live sheet's real historical data
# (only Income, Bills & Subscriptions, Expenses, and Debt/Mortgage Repayment were
# ever actually used); Savings and Investments have no rows to migrate. Income is
# an enumerated list per the verified table (unlike the Expense groups below,
# which are wildcards) since no other Income sub-category was ever real.
_INCOME_SUB_CATEGORIES = {"Salary", "Beem Adjustment"}
_EXPENSE_GROUPS = {"Bills & Subscriptions", "Expenses"}


def remap_type_category(legacy_category: str, legacy_sub_category: str) -> tuple[str, str]:
    if legacy_category == "Income" and legacy_sub_category in _INCOME_SUB_CATEGORIES:
        return "Income", legacy_sub_category
    if legacy_category in _EXPENSE_GROUPS:
        return "Expense", legacy_sub_category
    if legacy_category == "Debt" and legacy_sub_category == "Mortgage Repayment":
        return "Debt", "Mortgage Repayment"
    raise ValueError(
        f"No historical remap rule for legacy Category={legacy_category!r}, "
        f"Sub-category={legacy_sub_category!r}"
    )
