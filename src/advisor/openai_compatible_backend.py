import json
import urllib.request
from collections.abc import Mapping
from typing import Callable

from advisor.interface import CategoryHistory, MalformedResponseError, SuggestionResult
from advisor.prompt import build_prompt, parse_response


def _http_post(url: str, headers: dict, body: dict) -> dict:
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST"
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


class OpenAICompatibleAdvisor:
    """Generates a Budget Suggestion write-up via any OpenAI-compatible
    chat-completions HTTP endpoint - mirrors
    categorisation.openai_compatible_backend, minus the schema-constrained
    response_format: the write-up is free text, not a JSON contract.
    """

    def __init__(self, base_url: str, api_key: str, model: str, post: Callable[[str, dict, dict], dict] = _http_post):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._post = post

    def advise(self, history: list[CategoryHistory]) -> SuggestionResult:
        prompt = build_prompt(history)
        body = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self._api_key}"}

        try:
            response = self._post(f"{self._base_url}/chat/completions", headers, body)
        except Exception as exc:
            raise MalformedResponseError(f"OpenAI-compatible request failed: {exc}") from exc

        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise MalformedResponseError(f"Unexpected OpenAI-compatible response shape: {exc}") from exc

        if not isinstance(content, str):
            raise MalformedResponseError("OpenAI-compatible response content was not a string")

        return parse_response(content)


def connect(env: Mapping[str, str]) -> OpenAICompatibleAdvisor:
    """Build an OpenAICompatibleAdvisor from ADVISOR_OPENAI_COMPATIBLE_*
    settings - its own settings, not categorisation's OPENAI_COMPATIBLE_*
    ones, so the two pluggable backends can point at different
    endpoints/models (ADR-0014: nothing requires the same backend/model to be
    good at both judgement calls).
    """
    return OpenAICompatibleAdvisor(
        base_url=env["ADVISOR_OPENAI_COMPATIBLE_BASE_URL"],
        api_key=env.get("ADVISOR_OPENAI_COMPATIBLE_API_KEY", ""),
        model=env["ADVISOR_OPENAI_COMPATIBLE_MODEL"],
    )
