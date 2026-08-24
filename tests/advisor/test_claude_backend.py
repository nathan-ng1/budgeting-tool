import json

import pytest

from advisor.claude_backend import ClaudeCodeAdvisor
from advisor.interface import CategoryHistory, MalformedResponseError

HISTORY = [
    CategoryHistory(
        type="Expense",
        category="Groceries",
        last_month_actual=450.0,
        last_month_budgeted=400.0,
        trailing_average_actual=420.0,
        average_variance_pct=12.5,
    )
]


class FakeProcessRunner:
    def __init__(self, stdout: str):
        self.stdout = stdout
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> str:
        self.calls.append(args)
        return self.stdout


def envelope_with_result(write_up: str) -> str:
    return json.dumps({"type": "result", "subtype": "success", "result": write_up})


def test_invokes_claude_in_print_mode_with_json_output_format():
    runner = FakeProcessRunner(envelope_with_result("Groceries is trending over budget."))
    advisor = ClaudeCodeAdvisor(run_process=runner)

    advisor.advise(HISTORY)

    [args] = runner.calls
    assert args[0] == "claude"
    assert "-p" in args
    assert args[args.index("--output-format") + 1] == "json"


def test_prompt_is_passed_as_an_argument():
    runner = FakeProcessRunner(envelope_with_result("write-up"))
    advisor = ClaudeCodeAdvisor(run_process=runner)

    advisor.advise(HISTORY)

    [args] = runner.calls
    assert any("Groceries" in arg for arg in args)


def test_result_field_becomes_the_write_up():
    runner = FakeProcessRunner(envelope_with_result("Groceries is trending over budget."))
    advisor = ClaudeCodeAdvisor(run_process=runner)

    result = advisor.advise(HISTORY)

    assert result.write_up == "Groceries is trending over budget."


def test_non_json_stdout_raises_malformed_response_error():
    runner = FakeProcessRunner("not json")
    advisor = ClaudeCodeAdvisor(run_process=runner)

    with pytest.raises(MalformedResponseError):
        advisor.advise(HISTORY)


def test_envelope_missing_a_string_result_raises_malformed_response_error():
    runner = FakeProcessRunner(json.dumps({"type": "result"}))
    advisor = ClaudeCodeAdvisor(run_process=runner)

    with pytest.raises(MalformedResponseError):
        advisor.advise(HISTORY)


def test_empty_result_raises_malformed_response_error():
    runner = FakeProcessRunner(envelope_with_result("   "))
    advisor = ClaudeCodeAdvisor(run_process=runner)

    with pytest.raises(MalformedResponseError):
        advisor.advise(HISTORY)
