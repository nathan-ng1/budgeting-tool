import json

from categorisation.interface import BatchResult, CategoryResult, MalformedResponseError
from statement_export.parser import RawTransaction
from transaction_log.categories import Category, assignable_categories_by_type, types_with_categories

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
                    "type": {"type": ["string", "null"]},
                    "category": {"type": ["string", "null"]},
                    "needs_review": {"type": "boolean"},
                    "reason": {"type": ["string", "null"]},
                },
                "required": ["type", "category", "needs_review", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["results"],
    "additionalProperties": False,
}

RESPONSE_INSTRUCTIONS = """Respond with a single JSON object only - no prose, no markdown code \
fences - of exactly this shape:

{"results": [{"type": "...", "category": "...", "needs_review": true, "reason": "..."}]}

"results" must have exactly one object per transaction listed above, in the same order. Each \
object has exactly these keys:
- "type": one of the Type names listed above
- "category": one of that Type's Category names listed above
- "needs_review": true or false - true if you aren't confident in this assignment and want the \
user to confirm it
- "reason": a short one-sentence explanation, or null if needs_review is false"""


def build_prompt(transactions: list[RawTransaction], categories: list[Category]) -> str:
    assignable = assignable_categories_by_type(categories)
    type_lines = [
        f"- {transaction_type}: {', '.join(sorted(assignable[transaction_type]))}"
        for transaction_type in types_with_categories(assignable)
    ]
    transaction_lines = [
        f"{i}. date={transaction.date.isoformat()} amount={transaction.amount} notes={transaction.notes!r}"
        for i, transaction in enumerate(transactions)
    ]

    return (
        "You are categorising credit card / bank transactions for a personal budget.\n\n"
        "Assign each transaction a Type and Category from this fixed list:\n"
        + "\n".join(type_lines)
        + "\n\nTransactions:\n"
        + "\n".join(transaction_lines)
        + "\n\n"
        + RESPONSE_INSTRUCTIONS
    )


def parse_batch_response(raw: str, expected_count: int, categories: list[Category]) -> BatchResult:
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

    assignable = assignable_categories_by_type(categories)
    results = [_parse_result(i, item, assignable) for i, item in enumerate(results_data)]
    return BatchResult(results=results)


def _parse_result(index: int, item, assignable: dict[str, set[str]]) -> CategoryResult:
    if not isinstance(item, dict):
        raise MalformedResponseError(f"Result {index} is not a JSON object")

    try:
        transaction_type = item["type"]
        category = item["category"]
        needs_review = item["needs_review"]
    except KeyError as exc:
        raise MalformedResponseError(f"Result {index} is missing key {exc}") from exc

    if not isinstance(needs_review, bool):
        raise MalformedResponseError(f"Result {index}'s needs_review must be a boolean")

    reason = item.get("reason")
    if reason is not None and not isinstance(reason, str):
        raise MalformedResponseError(f"Result {index}'s reason must be a string or null")

    if not isinstance(transaction_type, str) or not isinstance(category, str):
        raise MalformedResponseError(f"Result {index}'s type/category must be strings")
    if category not in assignable.get(transaction_type, set()):
        raise MalformedResponseError(
            f"Result {index}: {category!r} is not a valid Category for {transaction_type!r}"
        )

    return CategoryResult(type=transaction_type, category=category, needs_review=needs_review, reason=reason)
