import json
from datetime import date

import pytest

from categorisation.claude_backend import ClaudeCodeCategoriser
from categorisation.interface import MalformedResponseError
from statement_export.parser import RawTransaction

CATEGORIES_BY_TYPE = {"Expense": {"Groceries"}}


def make_transaction(**overrides):
    defaults = dict(date=date(2026, 8, 5), amount=-42.50, notes="Woolworths")
    defaults.update(overrides)
    return RawTransaction(**defaults)


class FakeProcessRunner:
    def __init__(self, stdout: str):
        self.stdout = stdout
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> str:
        self.calls.append(args)
        return self.stdout


def batch_dict(transaction_type="Expense", category="Groceries", needs_review=False):
    return {"results": [{"type": transaction_type, "category": category, "needs_review": needs_review, "reason": None}]}


def envelope_with_structured_output(result: dict) -> str:
    return json.dumps({"type": "result", "subtype": "success", "result": json.dumps(result), "structured_output": result})


def envelope_with_result_only(result_text: str) -> str:
    return json.dumps({"type": "result", "subtype": "success", "result": result_text})


def test_invokes_claude_in_print_mode_with_json_output_format_and_a_json_schema():
    runner = FakeProcessRunner(envelope_with_structured_output(batch_dict()))
    categoriser = ClaudeCodeCategoriser(run_process=runner)

    categoriser.categorise([make_transaction()], CATEGORIES_BY_TYPE)

    [args] = runner.calls
    assert args[0] == "claude"
    assert "-p" in args
    assert args[args.index("--output-format") + 1] == "json"
    assert "--json-schema" in args


def test_prompt_is_passed_as_an_argument():
    runner = FakeProcessRunner(envelope_with_structured_output(batch_dict()))
    categoriser = ClaudeCodeCategoriser(run_process=runner)

    categoriser.categorise([make_transaction(notes="Woolworths")], CATEGORIES_BY_TYPE)

    [args] = runner.calls
    assert any("Woolworths" in arg for arg in args)


def test_structured_output_field_is_used_when_present():
    runner = FakeProcessRunner(envelope_with_structured_output(batch_dict(needs_review=True)))
    categoriser = ClaudeCodeCategoriser(run_process=runner)

    batch = categoriser.categorise([make_transaction()], CATEGORIES_BY_TYPE)

    assert len(batch.results) == 1
    assert batch.results[0].type == "Expense"
    assert batch.results[0].needs_review is True


def test_falls_back_to_the_result_field_when_structured_output_is_absent():
    runner = FakeProcessRunner(envelope_with_result_only(json.dumps(batch_dict())))
    categoriser = ClaudeCodeCategoriser(run_process=runner)

    batch = categoriser.categorise([make_transaction()], CATEGORIES_BY_TYPE)

    assert batch.results[0].type == "Expense"


def test_non_json_stdout_raises_malformed_response_error():
    runner = FakeProcessRunner("not json")
    categoriser = ClaudeCodeCategoriser(run_process=runner)

    with pytest.raises(MalformedResponseError):
        categoriser.categorise([make_transaction()], CATEGORIES_BY_TYPE)


def test_envelope_missing_both_structured_output_and_result_raises_malformed_response_error():
    runner = FakeProcessRunner(json.dumps({"type": "result"}))
    categoriser = ClaudeCodeCategoriser(run_process=runner)

    with pytest.raises(MalformedResponseError):
        categoriser.categorise([make_transaction()], CATEGORIES_BY_TYPE)


def test_result_text_that_is_not_the_expected_json_shape_raises_malformed_response_error():
    runner = FakeProcessRunner(envelope_with_result_only("some free-text reply, not JSON"))
    categoriser = ClaudeCodeCategoriser(run_process=runner)

    with pytest.raises(MalformedResponseError):
        categoriser.categorise([make_transaction()], CATEGORIES_BY_TYPE)
