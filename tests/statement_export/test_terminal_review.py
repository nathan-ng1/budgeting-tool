from datetime import date

from statement_export.parser import RawTransaction
from statement_export.terminal_review import TerminalReviewer

CATEGORIES_BY_TYPE = {
    "Expense": {"Groceries", "Dining & Takeaway"},
    "Income": {"Salary"},
}


def make_transaction(**overrides):
    defaults = dict(date=date(2026, 8, 5), amount=-42.50, notes="Woolworths")
    defaults.update(overrides)
    return RawTransaction(**defaults)


class FakeInput:
    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._responses.pop(0)


def test_valid_selections_return_the_chosen_type_and_category():
    # Types sorted: Expense(1), Income(2). Expense's Categories sorted:
    # Dining & Takeaway(1), Groceries(2).
    fake_input = FakeInput(["1", "2"])
    reviewer = TerminalReviewer(
        categories_by_type=CATEGORIES_BY_TYPE, input_fn=fake_input, print_fn=lambda *_: None
    )

    transaction_type, category = reviewer(make_transaction(), reason=None)

    assert transaction_type == "Expense"
    assert category == "Groceries"


def test_invalid_type_number_is_reprompted():
    fake_input = FakeInput(["99", "not a number", "2", "1"])
    reviewer = TerminalReviewer(
        categories_by_type=CATEGORIES_BY_TYPE, input_fn=fake_input, print_fn=lambda *_: None
    )

    transaction_type, category = reviewer(make_transaction(), reason=None)

    assert transaction_type == "Income"
    assert category == "Salary"


def test_invalid_category_number_is_reprompted():
    fake_input = FakeInput(["1", "99", "1"])
    reviewer = TerminalReviewer(
        categories_by_type=CATEGORIES_BY_TYPE, input_fn=fake_input, print_fn=lambda *_: None
    )

    transaction_type, category = reviewer(make_transaction(), reason=None)

    assert transaction_type == "Expense"
    assert category == "Dining & Takeaway"


def test_a_type_with_no_categories_is_not_offered():
    # Transfer has no Categories yet — offering it would drop the user into a
    # Category prompt with nothing valid to pick.
    printed = []
    fake_input = FakeInput(["2", "1"])
    reviewer = TerminalReviewer(
        categories_by_type={**CATEGORIES_BY_TYPE, "Transfer": set()},
        input_fn=fake_input,
        print_fn=printed.append,
    )

    transaction_type, category = reviewer(make_transaction(), reason=None)

    assert transaction_type == "Income"
    assert category == "Salary"
    assert "Transfer" not in "\n".join(printed)


def test_transaction_and_reason_are_printed():
    printed = []
    fake_input = FakeInput(["1", "1"])
    reviewer = TerminalReviewer(
        categories_by_type=CATEGORIES_BY_TYPE, input_fn=fake_input, print_fn=printed.append
    )

    reviewer(make_transaction(notes="Square Payment"), reason="might be a donation")

    joined = "\n".join(printed)
    assert "Square Payment" in joined
    assert "might be a donation" in joined
