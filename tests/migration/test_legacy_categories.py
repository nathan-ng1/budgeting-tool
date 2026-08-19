import pytest

from migration.legacy_categories import remap_type_category


@pytest.mark.parametrize(
    "legacy_category, legacy_sub_category, expected",
    [
        ("Income", "Salary", ("Income", "Salary")),
        ("Income", "Beem Adjustment", ("Income", "Beem Adjustment")),
        ("Bills & Subscriptions", "Subscriptions", ("Expense", "Subscriptions")),
        ("Bills & Subscriptions", "Insurance & Bills", ("Expense", "Insurance & Bills")),
        ("Expenses", "Groceries", ("Expense", "Groceries")),
        ("Expenses", "Dining & Takeaway", ("Expense", "Dining & Takeaway")),
        ("Debt", "Mortgage Repayment", ("Expense", "Mortgage Repayment")),
    ],
)
def test_remap_type_category_follows_the_verified_mechanical_table(
    legacy_category, legacy_sub_category, expected
):
    assert remap_type_category(legacy_category, legacy_sub_category) == expected


def test_remap_type_category_raises_for_an_unmapped_debt_sub_category():
    with pytest.raises(ValueError):
        remap_type_category("Debt", "Some Other Debt")


def test_remap_type_category_raises_for_an_unenumerated_income_sub_category():
    with pytest.raises(ValueError):
        remap_type_category("Income", "Rental")


@pytest.mark.parametrize("legacy_category", ["Savings", "Investments"])
def test_remap_type_category_raises_for_a_category_never_used_historically(legacy_category):
    with pytest.raises(ValueError):
        remap_type_category(legacy_category, "Anything")
