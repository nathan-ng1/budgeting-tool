import json
from datetime import date

import pytest

from categorisation.interface import MalformedResponseError
from categorisation.openai_compatible_backend import OpenAICompatibleCategoriser
from statement_export.parser import RawTransaction

CATEGORIES_BY_TYPE = {"Expense": {"Groceries"}}


def make_transaction(**overrides):
    defaults = dict(date=date(2026, 8, 5), amount=-42.50, notes="Woolworths")
    defaults.update(overrides)
    return RawTransaction(**defaults)


class FakeTransport:
    def __init__(self, response: dict):
        self.response = response
        self.calls: list[tuple[str, dict, dict]] = []

    def __call__(self, url: str, headers: dict, body: dict) -> dict:
        self.calls.append((url, headers, body))
        return self.response


def batch_json(transaction_type="Expense", category="Groceries", needs_review=False):
    return json.dumps(
        {
            "results": [
                {
                    "type": transaction_type,
                    "category": category,
                    "needs_review": needs_review,
                    "reason": None,
                }
            ]
        }
    )


def chat_completion_response(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def test_posts_to_chat_completions_under_the_configured_base_url():
    transport = FakeTransport(chat_completion_response(batch_json()))
    categoriser = OpenAICompatibleCategoriser(
        base_url="http://localhost:11434/v1", api_key="key", model="llama3", post=transport
    )

    categoriser.categorise([make_transaction()], CATEGORIES_BY_TYPE)

    [(url, headers, body)] = transport.calls
    assert url == "http://localhost:11434/v1/chat/completions"
    assert headers["Authorization"] == "Bearer key"
    assert body["model"] == "llama3"


def test_requests_schema_constrained_output():
    transport = FakeTransport(chat_completion_response(batch_json()))
    categoriser = OpenAICompatibleCategoriser(base_url="http://x", api_key="key", model="m", post=transport)

    categoriser.categorise([make_transaction()], CATEGORIES_BY_TYPE)

    [(_, _, body)] = transport.calls
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["schema"]["required"] == ["results"]


def test_trailing_slash_on_base_url_does_not_double_up():
    transport = FakeTransport(chat_completion_response(batch_json()))
    categoriser = OpenAICompatibleCategoriser(
        base_url="http://localhost:11434/v1/", api_key="key", model="llama3", post=transport
    )

    categoriser.categorise([make_transaction()], CATEGORIES_BY_TYPE)

    [(url, _, _)] = transport.calls
    assert url == "http://localhost:11434/v1/chat/completions"


def test_prompt_is_sent_as_a_user_message():
    transport = FakeTransport(chat_completion_response(batch_json()))
    categoriser = OpenAICompatibleCategoriser(base_url="http://x", api_key="key", model="m", post=transport)

    categoriser.categorise([make_transaction(notes="Woolworths")], CATEGORIES_BY_TYPE)

    [(_, _, body)] = transport.calls
    assert body["messages"] == [{"role": "user", "content": body["messages"][0]["content"]}]
    assert "Woolworths" in body["messages"][0]["content"]


def test_extracts_and_parses_message_content_into_a_batch_result():
    transport = FakeTransport(chat_completion_response(batch_json(needs_review=True)))
    categoriser = OpenAICompatibleCategoriser(base_url="http://x", api_key="key", model="m", post=transport)

    batch = categoriser.categorise([make_transaction()], CATEGORIES_BY_TYPE)

    assert len(batch.results) == 1
    assert batch.results[0].needs_review is True


def test_unexpected_response_shape_raises_malformed_response_error():
    transport = FakeTransport({"unexpected": "shape"})
    categoriser = OpenAICompatibleCategoriser(base_url="http://x", api_key="key", model="m", post=transport)

    with pytest.raises(MalformedResponseError):
        categoriser.categorise([make_transaction()], CATEGORIES_BY_TYPE)


def test_transport_failure_raises_malformed_response_error():
    def failing_transport(url, headers, body):
        raise ConnectionError("connection refused")

    categoriser = OpenAICompatibleCategoriser(base_url="http://x", api_key="key", model="m", post=failing_transport)

    with pytest.raises(MalformedResponseError):
        categoriser.categorise([make_transaction()], CATEGORIES_BY_TYPE)


def test_non_json_message_content_raises_malformed_response_error():
    transport = FakeTransport(chat_completion_response("not json"))
    categoriser = OpenAICompatibleCategoriser(base_url="http://x", api_key="key", model="m", post=transport)

    with pytest.raises(MalformedResponseError):
        categoriser.categorise([make_transaction()], CATEGORIES_BY_TYPE)
