import pytest

from advisor.interface import CategoryHistory, MalformedResponseError
from advisor.prompt import build_prompt, parse_response


def make_history(**overrides) -> CategoryHistory:
    defaults = dict(
        type="Expense",
        category="Groceries",
        last_month_actual=450.0,
        last_month_budgeted=400.0,
        trailing_average_actual=420.0,
        average_variance_pct=12.5,
    )
    defaults.update(overrides)
    return CategoryHistory(**defaults)


def test_prompt_includes_each_category_and_its_figures():
    prompt = build_prompt([make_history(category="Groceries", last_month_actual=450.0)])

    assert "Groceries" in prompt
    assert "450" in prompt


def test_prompt_covers_a_category_with_no_budgeted_or_variance_history():
    prompt = build_prompt([make_history(last_month_budgeted=None, trailing_average_actual=None, average_variance_pct=None)])

    # Doesn't crash formatting None - and says so rather than printing "None".
    assert "last month's budget=unset" in prompt
    assert "trailing average actual=unset" in prompt


def test_prompt_asks_for_plain_text_with_no_json_or_markdown():
    prompt = build_prompt([make_history()])

    assert "no JSON, no markdown" in prompt


def test_parse_response_strips_surrounding_whitespace():
    result = parse_response("  Groceries is trending over budget.  \n")

    assert result.write_up == "Groceries is trending over budget."


def test_parse_response_rejects_empty_text():
    with pytest.raises(MalformedResponseError):
        parse_response("   ")
