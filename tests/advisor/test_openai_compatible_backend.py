import pytest

from advisor.interface import CategoryHistory, MalformedResponseError
from advisor.openai_compatible_backend import OpenAICompatibleAdvisor

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


class FakeTransport:
    def __init__(self, response: dict):
        self.response = response
        self.calls: list[tuple[str, dict, dict]] = []

    def __call__(self, url: str, headers: dict, body: dict) -> dict:
        self.calls.append((url, headers, body))
        return self.response


def chat_completion_response(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def test_posts_to_chat_completions_under_the_configured_base_url():
    transport = FakeTransport(chat_completion_response("Groceries is trending over budget."))
    advisor = OpenAICompatibleAdvisor(base_url="http://localhost:11434/v1", api_key="key", model="llama3", post=transport)

    advisor.advise(HISTORY)

    [(url, headers, body)] = transport.calls
    assert url == "http://localhost:11434/v1/chat/completions"
    assert headers["Authorization"] == "Bearer key"
    assert body["model"] == "llama3"


def test_trailing_slash_on_base_url_does_not_double_up():
    transport = FakeTransport(chat_completion_response("write-up"))
    advisor = OpenAICompatibleAdvisor(base_url="http://localhost:11434/v1/", api_key="key", model="llama3", post=transport)

    advisor.advise(HISTORY)

    [(url, _, _)] = transport.calls
    assert url == "http://localhost:11434/v1/chat/completions"


def test_prompt_is_sent_as_a_user_message():
    transport = FakeTransport(chat_completion_response("write-up"))
    advisor = OpenAICompatibleAdvisor(base_url="http://x", api_key="key", model="m", post=transport)

    advisor.advise(HISTORY)

    [(_, _, body)] = transport.calls
    assert body["messages"] == [{"role": "user", "content": body["messages"][0]["content"]}]
    assert "Groceries" in body["messages"][0]["content"]


def test_extracts_message_content_into_the_write_up():
    transport = FakeTransport(chat_completion_response("Groceries is trending over budget."))
    advisor = OpenAICompatibleAdvisor(base_url="http://x", api_key="key", model="m", post=transport)

    result = advisor.advise(HISTORY)

    assert result.write_up == "Groceries is trending over budget."


def test_unexpected_response_shape_raises_malformed_response_error():
    transport = FakeTransport({"unexpected": "shape"})
    advisor = OpenAICompatibleAdvisor(base_url="http://x", api_key="key", model="m", post=transport)

    with pytest.raises(MalformedResponseError):
        advisor.advise(HISTORY)


def test_transport_failure_raises_malformed_response_error():
    def failing_transport(url, headers, body):
        raise ConnectionError("connection refused")

    advisor = OpenAICompatibleAdvisor(base_url="http://x", api_key="key", model="m", post=failing_transport)

    with pytest.raises(MalformedResponseError):
        advisor.advise(HISTORY)


def test_empty_message_content_raises_malformed_response_error():
    transport = FakeTransport(chat_completion_response("   "))
    advisor = OpenAICompatibleAdvisor(base_url="http://x", api_key="key", model="m", post=transport)

    with pytest.raises(MalformedResponseError):
        advisor.advise(HISTORY)
