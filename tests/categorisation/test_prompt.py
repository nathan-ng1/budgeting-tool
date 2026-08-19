import json
from datetime import date

import pytest

from categorisation.interface import MalformedResponseError
from categorisation.prompt import build_prompt, parse_batch_response
from statement_export.parser import RawTransaction

CATEGORIES_BY_TYPE = {
    "Expense": {"Groceries", "Dining & Takeaway"},
    "Income": {"Salary", "Beem Adjustment"},
}


def make_transaction(**overrides):
    defaults = dict(date=date(2026, 8, 5), amount=-42.50, notes="Woolworths")
    defaults.update(overrides)
    return RawTransaction(**defaults)


def test_prompt_lists_every_type_and_its_categories():
    prompt = build_prompt([make_transaction()], CATEGORIES_BY_TYPE)

    assert "Expense: Dining & Takeaway, Groceries" in prompt
    assert "Income: Beem Adjustment, Salary" in prompt


def test_prompt_omits_a_type_that_has_no_categories_yet():
    prompt = build_prompt([make_transaction()], {**CATEGORIES_BY_TYPE, "Transfer": set()})

    assert "Transfer" not in prompt


def test_prompt_lists_every_transaction_with_date_amount_and_notes():
    prompt = build_prompt(
        [make_transaction(notes="Woolworths"), make_transaction(notes="Coles")],
        CATEGORIES_BY_TYPE,
    )

    assert "2026-08-05" in prompt
    assert "-42.5" in prompt
    assert "Woolworths" in prompt
    assert "Coles" in prompt


def test_prompt_instructs_a_results_wrapped_json_object():
    prompt = build_prompt([make_transaction()], CATEGORIES_BY_TYPE)

    assert '"results"' in prompt
    assert "needs_review" in prompt


def test_valid_response_parses_into_a_batch_result_in_order():
    raw = json.dumps(
        {
            "results": [
                {"type": "Expense", "category": "Groceries", "needs_review": False, "reason": None},
                {"type": "Income", "category": "Salary", "needs_review": True, "reason": "unsure"},
            ]
        }
    )

    batch = parse_batch_response(raw, expected_count=2)

    assert [r.type for r in batch.results] == ["Expense", "Income"]
    assert [r.category for r in batch.results] == ["Groceries", "Salary"]
    assert [r.needs_review for r in batch.results] == [False, True]
    assert batch.results[1].reason == "unsure"


def test_reason_defaults_to_none_when_omitted():
    raw = json.dumps(
        {"results": [{"type": "Expense", "category": "Groceries", "needs_review": False}]}
    )

    batch = parse_batch_response(raw, expected_count=1)

    assert batch.results[0].reason is None


@pytest.mark.parametrize(
    "raw",
    [
        "not json at all",
        "[]",
        json.dumps({"results": "not a list"}),
        json.dumps({"nope": []}),
    ],
)
def test_structurally_invalid_response_raises_malformed_response_error(raw):
    with pytest.raises(MalformedResponseError):
        parse_batch_response(raw, expected_count=1)


def test_wrong_result_count_raises_malformed_response_error():
    raw = json.dumps(
        {"results": [{"type": "Expense", "category": "Groceries", "needs_review": False}]}
    )

    with pytest.raises(MalformedResponseError):
        parse_batch_response(raw, expected_count=2)


def test_missing_key_raises_malformed_response_error():
    raw = json.dumps({"results": [{"type": "Expense", "needs_review": False}]})

    with pytest.raises(MalformedResponseError):
        parse_batch_response(raw, expected_count=1)


def test_invalid_type_category_pair_raises_malformed_response_error():
    raw = json.dumps(
        {"results": [{"type": "Expense", "category": "Salary", "needs_review": False}]}
    )

    with pytest.raises(MalformedResponseError):
        parse_batch_response(raw, expected_count=1)


def test_non_boolean_needs_review_raises_malformed_response_error():
    raw = json.dumps(
        {"results": [{"type": "Expense", "category": "Groceries", "needs_review": "yes"}]}
    )

    with pytest.raises(MalformedResponseError):
        parse_batch_response(raw, expected_count=1)
