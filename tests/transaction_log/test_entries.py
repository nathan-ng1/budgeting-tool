import pytest

from transaction_log.entries import Candidate

# Candidate no longer validates its own (Type, Category) pair (Issue #91):
# Category is user-editable, per-instance data, so only whichever store call
# ends up persisting a Candidate can say whether a pair is valid - see
# database.store's _require_valid_pair and statement_export.orchestrator's
# valid_pairs check. This mirrors RecurringRule, which has never validated
# its own pair for the same reason.


def test_candidate_with_valid_type_and_category_pair_is_accepted(make_candidate):
    make_candidate(type="Expense", category="Subscriptions")


def test_candidate_with_zero_amount_is_rejected(make_candidate):
    with pytest.raises(ValueError):
        make_candidate(amount=0)


def test_candidate_accepts_a_negative_amount(make_candidate):
    # A raw Statement Export Transaction is negative-signed for spend (see
    # CONTEXT.md) — the writer normalises to positive when it writes, not the
    # Candidate itself, since Candidate carries the source transaction's sign.
    candidate = make_candidate(amount=-42.50)

    assert candidate.amount == -42.50
