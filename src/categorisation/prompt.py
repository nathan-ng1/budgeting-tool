import json

from categorisation.interface import BatchResult, CategoryResult, MalformedResponseError
from statement_export.parser import RawTransaction
from transaction_log.categories import is_valid_category_pair

# The structured-output contract every backend requests (schema-constrained where the backend
# supports it - claude_backend's --json-schema, openai_compatible_backend's response_format) and
# every backend's response is validated against via parse_batch_response below, regardless of
# whether the backend itself enforced it.
RESULTS_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "sub_category": {"type": "string"},
                    "needs_review": {"type": "boolean"},
                    "reason": {"type": ["string", "null"]},
                },
                "required": ["category", "sub_category", "needs_review", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["results"],
    "additionalProperties": False,
}

RESPONSE_INSTRUCTIONS = """Respond with a single JSON object only - no prose, no markdown code \
fences - of exactly this shape:

{"results": [{"category": "...", "sub_category": "...", "needs_review": true, "reason": "..."}]}

"results" must have exactly one object per transaction listed above, in the same order. Each \
object has exactly these keys:
- "category": one of the Category names listed above
- "sub_category": one of that Category's Sub-category names listed above
- "needs_review": true or false - true if you aren't confident in this assignment and want the \
user to confirm it
- "reason": a short one-sentence explanation, or null if needs_review is false"""


def build_prompt(transactions: list[RawTransaction], category_list: dict[str, set[str]]) -> str:
    category_lines = [
        f"- {category}: {', '.join(sorted(sub_categories))}"
        for category, sub_categories in sorted(category_list.items())
    ]
    transaction_lines = [
        f"{i}. date={transaction.date.isoformat()} amount={transaction.amount} notes={transaction.notes!r}"
        for i, transaction in enumerate(transactions)
    ]

    return (
        "You are categorising credit card / bank transactions for a personal budget.\n\n"
        "Assign each transaction a Category and Sub-category from this fixed list:\n"
        + "\n".join(category_lines)
        + "\n\nTransactions:\n"
        + "\n".join(transaction_lines)
        + "\n\n"
        + RESPONSE_INSTRUCTIONS
    )


def parse_batch_response(raw: str, expected_count: int) -> BatchResult:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MalformedResponseError(f"Response was not valid JSON: {exc}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise MalformedResponseError("Expected a JSON object with a 'results' array")

    results_data = data["results"]
    if len(results_data) != expected_count:
        raise MalformedResponseError(
            f"Expected {expected_count} results, got {len(results_data)}"
        )

    results = [_parse_result(i, item) for i, item in enumerate(results_data)]
    return BatchResult(results=results)


def _parse_result(index: int, item) -> CategoryResult:
    if not isinstance(item, dict):
        raise MalformedResponseError(f"Result {index} is not a JSON object")

    try:
        category = item["category"]
        sub_category = item["sub_category"]
        needs_review = item["needs_review"]
    except KeyError as exc:
        raise MalformedResponseError(f"Result {index} is missing key {exc}") from exc

    if not isinstance(category, str) or not isinstance(sub_category, str):
        raise MalformedResponseError(f"Result {index}'s category/sub_category must be strings")
    if not isinstance(needs_review, bool):
        raise MalformedResponseError(f"Result {index}'s needs_review must be a boolean")
    if not is_valid_category_pair(category, sub_category):
        raise MalformedResponseError(
            f"Result {index}: {sub_category!r} is not a valid Sub-category for {category!r}"
        )

    reason = item.get("reason")
    if reason is not None and not isinstance(reason, str):
        raise MalformedResponseError(f"Result {index}'s reason must be a string or null")

    return CategoryResult(category=category, sub_category=sub_category, needs_review=needs_review, reason=reason)
