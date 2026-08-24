import pytest

from advisor.codex_backend import CodexAdvisor
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


def test_invokes_codex_exec_with_the_prompt():
    runner = FakeProcessRunner("Groceries is trending over budget.")
    advisor = CodexAdvisor(run_process=runner)

    advisor.advise(HISTORY)

    [args] = runner.calls
    assert args[0] == "codex"
    assert args[1] == "exec"
    assert any("Groceries" in arg for arg in args)


def test_stdout_becomes_the_write_up():
    runner = FakeProcessRunner("  Groceries is trending over budget.  \n")
    advisor = CodexAdvisor(run_process=runner)

    result = advisor.advise(HISTORY)

    assert result.write_up == "Groceries is trending over budget."


def test_empty_stdout_raises_malformed_response_error():
    runner = FakeProcessRunner("   ")
    advisor = CodexAdvisor(run_process=runner)

    with pytest.raises(MalformedResponseError):
        advisor.advise(HISTORY)
