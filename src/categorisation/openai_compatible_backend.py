import json
import urllib.request
from collections.abc import Mapping
from typing import Callable

from categorisation.interface import BatchResult, MalformedResponseError
from categorisation.prompt import RESULTS_JSON_SCHEMA, build_prompt, parse_batch_response
from statement_export.parser import RawTransaction
from transaction_log.categories import Category


def _http_post(url: str, headers: dict, body: dict) -> dict:
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST"
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


class OpenAICompatibleCategoriser:
    """Categorises via any OpenAI-compatible chat-completions HTTP endpoint.

    Covers local Ollama (pointed at its own OpenAI-compatible endpoint) and
    any other compatible provider (OpenAI itself, OpenRouter, LM Studio,
    etc.) via a configurable base URL, API key, and model name. Requests
    schema-constrained output via response_format's json_schema type where
    the endpoint honours it; parse_batch_response still re-validates the
    result regardless, since not every OpenAI-compatible server enforces it.

    Verified against a real local Ollama endpoint (qwen3.5:9b): the request/response contract
    works end-to-end (small batches categorise correctly, including sensible needs_review
    flags), but a full statement-sized batch (125 transactions) exhausted the model's context
    before finishing, and parse_batch_response's expected-count check correctly caught the
    truncated result and aborted cleanly rather than writing partial data. Not practically usable
    against a small local model without further work (larger context, disabling "thinking" mode,
    or batching) - see docs/agents/statement-export-pipeline.md's "Manual backend verification"
    section for details.
    """

    def __init__(self, base_url: str, api_key: str, model: str, post: Callable[[str, dict, dict], dict] = _http_post):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._post = post

    def categorise(self, transactions: list[RawTransaction], categories: list[Category]) -> BatchResult:
        prompt = build_prompt(transactions, categories)
        body = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "categorisation_results", "schema": RESULTS_JSON_SCHEMA, "strict": True},
            },
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

        return parse_batch_response(content, expected_count=len(transactions), categories=categories)


def connect(env: Mapping[str, str]) -> OpenAICompatibleCategoriser:
    """Build an OpenAICompatibleCategoriser from OPENAI_COMPATIBLE_* settings.

    Takes the configuration to read rather than reaching for the environment
    itself, so the caller decides where the settings come from (Issue #30).
    """
    return OpenAICompatibleCategoriser(
        base_url=env["OPENAI_COMPATIBLE_BASE_URL"],
        api_key=env.get("OPENAI_COMPATIBLE_API_KEY", ""),
        model=env["OPENAI_COMPATIBLE_MODEL"],
    )
