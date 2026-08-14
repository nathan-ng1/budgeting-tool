import json
from datetime import date

import pytest

from categorisation.claude_backend import ClaudeCodeCategoriser
from categorisation.interface import MalformedResponseError
from statement_export.parser import RawTransaction

CATEGORY_LIST = {"Expenses": {"Groceries"}}


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


def envelope(result_text: str) -> str:
    return json.dumps({"type": "result", "subtype": "success", "result": result_text})


def batch_json(category="Expenses", sub_category="Groceries", needs_review=False):
    return json.dumps(
        {"results": [{"category": category, "sub_category": sub_category, "needs_review": needs_review, "reason": None}]}
    )


def test_invokes_claude_in_print_mode_with_json_output_format():
    runner = FakeProcessRunner(envelope(batch_json()))
    categoriser = ClaudeCodeCategoriser(run_process=runner)

    categoriser.categorise([make_transaction()], CATEGORY_LIST)

    [args] = runner.calls
    assert args[0] == "claude"
    assert "-p" in args
    assert "--output-format" in args
    assert args[args.index("--output-format") + 1] == "json"


def test_prompt_is_passed_as_an_argument():
    runner = FakeProcessRunner(envelope(batch_json()))
    categoriser = ClaudeCodeCategoriser(run_process=runner)

    categoriser.categorise([make_transaction(notes="Woolworths")], CATEGORY_LIST)

    [args] = runner.calls
    assert any("Woolworths" in arg for arg in args)


def test_extracts_and_parses_the_result_field_into_a_batch_result():
    runner = FakeProcessRunner(envelope(batch_json(needs_review=True)))
    categoriser = ClaudeCodeCategoriser(run_process=runner)

    batch = categoriser.categorise([make_transaction()], CATEGORY_LIST)

    assert len(batch.results) == 1
    assert batch.results[0].category == "Expenses"
    assert batch.results[0].needs_review is True


def test_non_json_stdout_raises_malformed_response_error():
    runner = FakeProcessRunner("not json")
    categoriser = ClaudeCodeCategoriser(run_process=runner)

    with pytest.raises(MalformedResponseError):
        categoriser.categorise([make_transaction()], CATEGORY_LIST)


def test_envelope_missing_result_field_raises_malformed_response_error():
    runner = FakeProcessRunner(json.dumps({"type": "result"}))
    categoriser = ClaudeCodeCategoriser(run_process=runner)

    with pytest.raises(MalformedResponseError):
        categoriser.categorise([make_transaction()], CATEGORY_LIST)


def test_inner_result_text_that_is_not_the_expected_json_shape_raises_malformed_response_error():
    runner = FakeProcessRunner(envelope("some free-text reply, not JSON"))
    categoriser = ClaudeCodeCategoriser(run_process=runner)

    with pytest.raises(MalformedResponseError):
        categoriser.categorise([make_transaction()], CATEGORY_LIST)


def test_model_override_is_passed_through():
    runner = FakeProcessRunner(envelope(batch_json()))
    categoriser = ClaudeCodeCategoriser(run_process=runner, model="claude-haiku-4-5")

    categoriser.categorise([make_transaction()], CATEGORY_LIST)

    [args] = runner.calls
    assert "--model" in args
    assert args[args.index("--model") + 1] == "claude-haiku-4-5"
