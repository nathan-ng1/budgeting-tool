import json
from datetime import date

import pytest

from categorisation.codex_backend import CodexCategoriser
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


def batch_json(category="Expenses", sub_category="Groceries", needs_review=False):
    return json.dumps(
        {"results": [{"category": category, "sub_category": sub_category, "needs_review": needs_review, "reason": None}]}
    )


def test_invokes_codex_exec_non_interactively():
    runner = FakeProcessRunner(batch_json())
    categoriser = CodexCategoriser(run_process=runner)

    categoriser.categorise([make_transaction()], CATEGORY_LIST)

    [args] = runner.calls
    assert args[0] == "codex"
    assert args[1] == "exec"


def test_prompt_is_passed_as_an_argument():
    runner = FakeProcessRunner(batch_json())
    categoriser = CodexCategoriser(run_process=runner)

    categoriser.categorise([make_transaction(notes="Woolworths")], CATEGORY_LIST)

    [args] = runner.calls
    assert any("Woolworths" in arg for arg in args)


def test_stdout_is_the_final_message_and_parses_directly_into_a_batch_result():
    runner = FakeProcessRunner(batch_json(needs_review=True))
    categoriser = CodexCategoriser(run_process=runner)

    batch = categoriser.categorise([make_transaction()], CATEGORY_LIST)

    assert len(batch.results) == 1
    assert batch.results[0].category == "Expenses"
    assert batch.results[0].needs_review is True


def test_non_json_stdout_raises_malformed_response_error():
    runner = FakeProcessRunner("not json")
    categoriser = CodexCategoriser(run_process=runner)

    with pytest.raises(MalformedResponseError):
        categoriser.categorise([make_transaction()], CATEGORY_LIST)
