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
    # A Type with no Categories yet — offering it would drop the user into a
    # Category prompt with nothing valid to pick.
    printed = []
    fake_input = FakeInput(["2", "1"])
    reviewer = TerminalReviewer(
        categories_by_type={**CATEGORIES_BY_TYPE, "Debt": set()},
        input_fn=fake_input,
        print_fn=printed.append,
    )

    transaction_type, category = reviewer(make_transaction(), reason=None)

    assert transaction_type == "Income"
    assert category == "Salary"
    assert "Debt" not in "\n".join(printed)


def test_savings_stays_out_of_type_options_even_with_real_categories():
    # ADR-0022 - TerminalReviewer offers whatever types_with_categories()
    # returns, which now excludes Savings outright (AI_EXCLUDED_TYPES), not
    # just Types with an empty Category set.
    printed = []
    fake_input = FakeInput(["2", "1"])
    reviewer = TerminalReviewer(
        categories_by_type={**CATEGORIES_BY_TYPE, "Savings": {"Savings", "Investments"}},
        input_fn=fake_input,
        print_fn=printed.append,
    )

    transaction_type, category = reviewer(make_transaction(), reason=None)

    assert transaction_type == "Income"
    assert category == "Salary"
    assert "Savings" not in "\n".join(printed)


def test_drop_transaction_option_is_offered_for_a_positive_amount_transaction():
    # Types sorted: Expense(1), Income(2), then Drop — Don't Record(3).
    printed = []
    fake_input = FakeInput(["3"])
    reviewer = TerminalReviewer(
        categories_by_type=CATEGORIES_BY_TYPE, input_fn=fake_input, print_fn=printed.append
    )

    result = reviewer(make_transaction(amount=2143.68, notes="PAYMENT - THANKYOU"), reason=None)

    assert result is None
    assert "Drop — Don't Record" in "\n".join(printed)


def test_drop_transaction_option_is_also_offered_for_a_negative_amount_transaction():
    # ADR-0016 - the "don't record this" escape hatch is generic, not tied to
    # positive-Amount Bill Payments any more.
    printed = []
    fake_input = FakeInput(["3"])
    reviewer = TerminalReviewer(
        categories_by_type=CATEGORIES_BY_TYPE, input_fn=fake_input, print_fn=printed.append
    )

    result = reviewer(make_transaction(amount=-42.50), reason=None)

    assert result is None
    assert "Drop — Don't Record" in "\n".join(printed)


def test_choosing_a_type_after_declining_to_drop_still_works():
    fake_input = FakeInput(["1", "2"])
    reviewer = TerminalReviewer(
        categories_by_type=CATEGORIES_BY_TYPE, input_fn=fake_input, print_fn=lambda *_: None
    )

    result = reviewer(make_transaction(amount=-42.50, notes="Woolworths"), reason=None)

    assert result == ("Expense", "Groceries")


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
