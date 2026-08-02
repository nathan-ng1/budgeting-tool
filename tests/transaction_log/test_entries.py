import pytest

from transaction_log.entries import Candidate


def test_candidate_with_valid_category_and_sub_category_pair_is_accepted(make_candidate):
    make_candidate(category="Bills & Subscriptions", sub_category="Subscriptions")


@pytest.mark.parametrize(
    "category,sub_category",
    [
        ("Expenses", "Subscriptions"),  # Subscriptions belongs to Bills & Subscriptions, not Expenses
        ("Bills & Subscriptions", "Groceries"),  # Groceries belongs to Expenses
        ("Income", "Mortgage Repayment"),  # Mortgage Repayment belongs to Debt
        ("Made Up Category", "Made Up Sub-Category"),
    ],
)
def test_candidate_with_sub_category_not_matching_its_fixed_category_is_rejected(
    make_candidate, category, sub_category
):
    with pytest.raises(ValueError):
        make_candidate(category=category, sub_category=sub_category)


def test_candidate_with_zero_amount_is_rejected(make_candidate):
    with pytest.raises(ValueError):
        make_candidate(amount=0)


def test_candidate_accepts_a_negative_amount(make_candidate):
    # A raw Statement Export Transaction is negative-signed for spend (see
    # CONTEXT.md) — the writer normalises to positive when it writes, not the
    # Candidate itself, since Candidate carries the source transaction's sign.
    candidate = make_candidate(amount=-42.50)

    assert candidate.amount == -42.50
