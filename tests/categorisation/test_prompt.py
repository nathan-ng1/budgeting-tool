import json
from datetime import date

import pytest

from categorisation.interface import MalformedResponseError
from categorisation.prompt import build_prompt, parse_batch_response
from statement_export.parser import RawTransaction
from transaction_log.categories import Category

CATEGORIES = [
    Category(id=1, type="Expense", name="Groceries", emoji=None, locked=False),
    Category(id=2, type="Expense", name="Dining & Takeaway", emoji=None, locked=False),
    Category(id=3, type="Expense", name="Beem Adjustment", emoji=None, locked=True),
    Category(id=4, type="Income", name="Salary", emoji=None, locked=False),
]


def make_transaction(**overrides):
    defaults = dict(date=date(2026, 8, 5), amount=-42.50, notes="Woolworths")
    defaults.update(overrides)
    return RawTransaction(**defaults)


def test_prompt_lists_every_type_and_its_categories():
    prompt = build_prompt([make_transaction()], CATEGORIES)

    assert "Expense: Dining & Takeaway, Groceries" in prompt
    assert "Income: Salary" in prompt


def test_prompt_never_lists_beem_adjustment_as_an_assignable_category():
    # ADR-0015 - Beem Adjustment must only ever be produced by the
    # deterministic Beem parser path, never model-assigned, even though it's
    # present in the categories dict passed in.
    prompt = build_prompt([make_transaction()], CATEGORIES)

    assert "Beem Adjustment" not in prompt


def test_prompt_omits_a_type_that_has_no_categories_yet():
    # A locked-only Type (Debt here, absent elsewhere in CATEGORIES) ends up
    # with an empty assignable set, same as a Type with no Categories at all
    # - both are omitted.
    categories = [*CATEGORIES, Category(id=5, type="Debt", name="Some Locked Debt", emoji=None, locked=True)]

    prompt = build_prompt([make_transaction()], categories)

    assert "Debt" not in prompt


def test_prompt_omits_savings_even_with_real_non_locked_categories():
    # ADR-0022 - Savings must stay out of the categorisation prompt for a
    # reason separate from "locked" or "has no categories yet": it's
    # AI-excluded outright, even with real, unlocked Categories to offer.
    categories = [
        *CATEGORIES,
        Category(id=5, type="Savings", name="Savings", emoji=None, locked=False),
        Category(id=6, type="Savings", name="Investments", emoji=None, locked=False),
    ]

    prompt = build_prompt([make_transaction()], categories)

    assert "Savings" not in prompt
    assert "Investments" not in prompt


def test_prompt_lists_every_transaction_with_date_amount_and_notes():
    prompt = build_prompt(
        [make_transaction(notes="Woolworths"), make_transaction(notes="Coles")],
        CATEGORIES,
    )

    assert "2026-08-05" in prompt
    assert "-42.5" in prompt
    assert "Woolworths" in prompt
    assert "Coles" in prompt


def test_prompt_instructs_a_results_wrapped_json_object():
    prompt = build_prompt([make_transaction()], CATEGORIES)

    assert '"results"' in prompt
    assert "needs_review" in prompt


def test_valid_response_parses_into_a_batch_result_in_order():
    raw = json.dumps(
        {
            "results": [
                {
                    "type": "Expense",
                    "category": "Groceries",
                    "needs_review": False,
                    "reason": None,
                },
                {
                    "type": "Income",
                    "category": "Salary",
                    "needs_review": True,
                    "reason": "unsure",
                },
            ]
        }
    )

    batch = parse_batch_response(raw, expected_count=2, categories=CATEGORIES)

    assert [r.type for r in batch.results] == ["Expense", "Income"]
    assert [r.category for r in batch.results] == ["Groceries", "Salary"]
    assert [r.needs_review for r in batch.results] == [False, True]
    assert batch.results[1].reason == "unsure"


def test_reason_defaults_to_none_when_omitted():
    raw = json.dumps(
        {
            "results": [
                {
                    "type": "Expense",
                    "category": "Groceries",
                    "needs_review": False,
                }
            ]
        }
    )

    batch = parse_batch_response(raw, expected_count=1, categories=CATEGORIES)

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
        parse_batch_response(raw, expected_count=1, categories=CATEGORIES)


def test_wrong_result_count_raises_malformed_response_error():
    raw = json.dumps(
        {
            "results": [
                {
                    "type": "Expense",
                    "category": "Groceries",
                    "needs_review": False,
                }
            ]
        }
    )

    with pytest.raises(MalformedResponseError):
        parse_batch_response(raw, expected_count=2, categories=CATEGORIES)


def test_missing_key_raises_malformed_response_error():
    raw = json.dumps({"results": [{"type": "Expense", "needs_review": False}]})

    with pytest.raises(MalformedResponseError):
        parse_batch_response(raw, expected_count=1, categories=CATEGORIES)


def test_invalid_type_category_pair_raises_malformed_response_error():
    raw = json.dumps(
        {
            "results": [
                {
                    "type": "Expense",
                    "category": "Salary",
                    "needs_review": False,
                }
            ]
        }
    )

    with pytest.raises(MalformedResponseError):
        parse_batch_response(raw, expected_count=1, categories=CATEGORIES)


def test_a_locked_category_returned_by_the_model_is_rejected():
    # ADR-0015 - Beem Adjustment must only ever be produced by the
    # deterministic Beem parser path, never model-assigned, even though it's
    # a real Expense Category (mirrors what build_prompt withholds from it).
    raw = json.dumps(
        {
            "results": [
                {
                    "type": "Expense",
                    "category": "Beem Adjustment",
                    "needs_review": False,
                }
            ]
        }
    )

    with pytest.raises(MalformedResponseError):
        parse_batch_response(raw, expected_count=1, categories=CATEGORIES)


def test_a_category_added_since_the_prompt_was_built_is_accepted():
    # Issue #90/#92 - validation reads the live `categories` table passed in,
    # not a hardcoded dict, so a Category added via Category Management is
    # immediately assignable.
    raw = json.dumps(
        {
            "results": [
                {
                    "type": "Expense",
                    "category": "Pet Care",
                    "needs_review": False,
                }
            ]
        }
    )
    categories = [*CATEGORIES, Category(id=6, type="Expense", name="Pet Care", emoji=None, locked=False)]

    batch = parse_batch_response(raw, expected_count=1, categories=categories)

    assert batch.results[0].category == "Pet Care"


def test_non_boolean_needs_review_raises_malformed_response_error():
    raw = json.dumps(
        {
            "results": [
                {
                    "type": "Expense",
                    "category": "Groceries",
                    "needs_review": "yes",
                }
            ]
        }
    )

    with pytest.raises(MalformedResponseError):
        parse_batch_response(raw, expected_count=1, categories=CATEGORIES)
