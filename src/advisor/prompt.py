from advisor.interface import CategoryHistory, MalformedResponseError, SuggestionResult

RESPONSE_INSTRUCTIONS = """Respond with the write-up itself only - plain text, no JSON, no markdown \
code fences, no preamble. A few short paragraphs is enough: call out which Categories are \
running over or under Budgeted, and any Category worth a closer look next time Category \
Budgets are set."""


def build_prompt(history: list[CategoryHistory]) -> str:
    lines = [_history_line(row) for row in history]

    return (
        "You are a personal budgeting advisor. Analyse this Financial Year's recent "
        "Budgeted-vs-Actual history for these Expense and Debt Categories and write a short "
        "analysis to help set next month's Category Budgets. Income is deliberately excluded - "
        "don't comment on it.\n\n"
        + "\n".join(lines)
        + "\n\n"
        + RESPONSE_INSTRUCTIONS
    )


def _history_line(row: CategoryHistory) -> str:
    return (
        f"- {row.type} / {row.category}: last month's actual={row.last_month_actual:.2f}, "
        f"last month's budget={_fmt(row.last_month_budgeted)}, "
        f"trailing average actual={_fmt(row.trailing_average_actual)}, "
        f"average variance={_fmt_pct(row.average_variance_pct)}"
    )


def _fmt(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "unset"


def _fmt_pct(value: float | None) -> str:
    return f"{value:+.1f}%" if value is not None else "no budget history to compare against"


def parse_response(raw: str) -> SuggestionResult:
    write_up = raw.strip()
    if not write_up:
        raise MalformedResponseError("Response was empty")
    return SuggestionResult(write_up=write_up)
