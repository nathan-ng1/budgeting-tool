import pytest

from transaction_log.entries import Candidate


def test_candidate_with_valid_type_and_category_pair_is_accepted(make_candidate):
    make_candidate(type="Expense", category="Subscriptions")


@pytest.mark.parametrize(
    "transaction_type,category",
    [
        ("Income", "Subscriptions"),  # Subscriptions is an Expense Category
        ("Expense", "Salary"),  # Salary is an Income Category
        ("Income", "Mortgage Repayment"),  # Mortgage Repayment is an Expense Category
        ("Transfer", "Groceries"),  # Transfer has no Categories yet
        ("Made Up Type", "Made Up Category"),
    ],
)
def test_candidate_with_category_not_matching_its_fixed_type_is_rejected(
    make_candidate, transaction_type, category
):
    with pytest.raises(ValueError):
        make_candidate(type=transaction_type, category=category)


def test_candidate_with_zero_amount_is_rejected(make_candidate):
    with pytest.raises(ValueError):
        make_candidate(amount=0)


def test_candidate_accepts_a_negative_amount(make_candidate):
    # A raw Statement Export Transaction is negative-signed for spend (see
    # CONTEXT.md) — the writer normalises to positive when it writes, not the
    # Candidate itself, since Candidate carries the source transaction's sign.
    candidate = make_candidate(amount=-42.50)

    assert candidate.amount == -42.50
