import pytest

from transaction_log.categories import (
    CATEGORIES_BY_TYPE,
    is_valid_type_category_pair,
    types_with_categories,
)


def test_the_three_types_are_income_expense_and_transfer():
    assert set(CATEGORIES_BY_TYPE) == {"Income", "Expense", "Transfer"}


def test_transfer_has_no_categories_yet():
    # Transfer Categories are added lazily, only for real cases (CONTEXT.md).
    assert CATEGORIES_BY_TYPE["Transfer"] == set()


@pytest.mark.parametrize(
    "transaction_type,category",
    [
        ("Income", "Salary"),
        ("Income", "Beem Adjustment"),
        ("Income", "Rental"),
        ("Income", "Refund"),
        ("Expense", "Groceries"),
        ("Expense", "Subscriptions"),
        ("Expense", "Rental Expense"),
        ("Expense", "Mortgage Repayment"),
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
        ("Debt", "Mortgage Repayment"),  # Debt is a retired Type
        ("Made Up Type", "Made Up Category"),
    ],
)
def test_a_category_under_the_wrong_type_is_rejected(transaction_type, category):
    assert not is_valid_type_category_pair(transaction_type, category)


def test_types_with_categories_omits_a_type_that_has_none_yet():
    assert types_with_categories() == ["Expense", "Income"]


def test_types_with_categories_accepts_an_explicit_mapping():
    assert types_with_categories({"B": {"x"}, "A": {"y"}, "C": set()}) == ["A", "B"]
