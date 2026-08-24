import pytest

from transaction_log.categories import (
    CATEGORIES_BY_TYPE,
    TYPE_ORDER,
    Category,
    assignable_categories_by_type,
    is_valid_type_category_pair,
    type_for_category,
    types_with_categories,
)


def test_the_four_types_are_income_expense_debt_and_transfer():
    assert set(CATEGORIES_BY_TYPE) == {"Income", "Expense", "Debt", "Transfer"}


def test_type_order_is_income_expense_debt_transfer():
    # CONTEXT.md's own definition order - what the Types filter and the
    # Transaction/Recurring Rule forms' Type selects display, as opposed to
    # types_with_categories()'s alphabetical order below.
    assert TYPE_ORDER == ("Income", "Expense", "Debt", "Transfer")


def test_transfer_has_no_categories_yet():
    # Transfer Categories are added lazily, only for real cases (CONTEXT.md).
    assert CATEGORIES_BY_TYPE["Transfer"] == set()


@pytest.mark.parametrize(
    "transaction_type,category",
    [
        ("Income", "Salary"),
        ("Income", "Rental"),
        ("Expense", "Groceries"),
        ("Expense", "Subscriptions"),
        ("Expense", "Rental Expense"),
        ("Expense", "Beem Adjustment"),
        ("Debt", "Mortgage Repayment"),
    ],
)
def test_a_category_validates_under_its_own_type(transaction_type, category):
    assert is_valid_type_category_pair(transaction_type, category)


@pytest.mark.parametrize(
    "transaction_type,category",
    [
        ("Income", "Groceries"),  # Groceries is an Expense
        ("Expense", "Salary"),  # Salary is Income
        ("Transfer", "Groceries"),  # Transfer has no Categories at all
        ("Expense", "Mortgage Repayment"),  # Mortgage Repayment moved to Debt
        ("Income", "Beem Adjustment"),  # ADR-0015 - moved to Expense
        ("Income", "Refund"),  # ADR-0016 - retired entirely
        ("Expense", "Refund"),  # ADR-0016 - retired entirely
        ("Made Up Type", "Made Up Category"),
    ],
)
def test_a_category_under_the_wrong_type_is_rejected(transaction_type, category):
    assert not is_valid_type_category_pair(transaction_type, category)


def test_beem_adjustment_type_is_expense():
    # ADR-0015 - Beem Adjustment reduces Expense instead of counting as Income.
    assert type_for_category("Beem Adjustment") == "Expense"


def test_refund_has_no_type():
    # ADR-0016 - Refund is retired, not a valid Category under any Type.
    assert type_for_category("Refund") is None


def test_assignable_categories_by_type_excludes_locked_categories():
    # ADR-0015 - a locked Category (Beem Adjustment today) must only ever be
    # produced by the deterministic Beem parser path, never offered to the
    # categorisation prompt as somewhere to file an ordinary card transaction.
    categories = [
        Category(id=1, type="Expense", name="Beem Adjustment", emoji=None, locked=True),
        Category(id=2, type="Expense", name="Groceries", emoji=None, locked=False),
        Category(id=3, type="Income", name="Salary", emoji=None, locked=False),
    ]

    assignable = assignable_categories_by_type(categories)

    assert assignable == {"Expense": {"Groceries"}, "Income": {"Salary"}}


def test_assignable_categories_by_type_keeps_a_type_with_only_locked_categories():
    # A locked-only Type still appears (empty), just like Transfer does today
    # for types_with_categories - it isn't dropped outright.
    categories = [Category(id=1, type="Expense", name="Beem Adjustment", emoji=None, locked=True)]

    assignable = assignable_categories_by_type(categories)

    assert assignable == {"Expense": set()}


def test_assignable_categories_by_type_excludes_any_locked_category_generically():
    # Not name-specific - any Category flagged locked is excluded, not just
    # "Beem Adjustment" by name (the Further Note in #89).
    categories = [Category(id=1, type="Debt", name="Some Other Adjustment", emoji=None, locked=True)]

    assignable = assignable_categories_by_type(categories)

    assert assignable == {"Debt": set()}


def test_types_with_categories_omits_a_type_that_has_none_yet():
    assert types_with_categories() == ["Debt", "Expense", "Income"]


def test_types_with_categories_accepts_an_explicit_mapping():
    assert types_with_categories({"B": {"x"}, "A": {"y"}, "C": set()}) == ["A", "B"]
