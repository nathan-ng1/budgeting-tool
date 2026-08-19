import json
import subprocess
from typing import Callable

from categorisation.interface import BatchResult, MalformedResponseError
from categorisation.prompt import RESULTS_JSON_SCHEMA, build_prompt, parse_batch_response
from statement_export.parser import RawTransaction


def _run_subprocess(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


class ClaudeCodeCategoriser:
    """Categorises via Claude Code's own non-interactive `claude -p` mode.

    Uses whatever auth Claude Code is already configured with - no separate
    Anthropic API key or billing involved. Passes --json-schema so Claude
    Code itself validates the response shape; the envelope's structured_output
    field (a parsed dict) is used when present, falling back to its result
    field (a JSON string) otherwise - both are still re-validated via
    parse_batch_response, since schema-constrained output is a stronger hint,
    not a guarantee.
    """

    def __init__(self, run_process: Callable[[list[str]], str] = _run_subprocess):
        self._run_process = run_process

    def categorise(self, transactions: list[RawTransaction], categories_by_type: dict[str, set[str]]) -> BatchResult:
        prompt = build_prompt(transactions, categories_by_type)
        args = [
            "claude", "-p", prompt,
            "--output-format", "json",
            "--json-schema", json.dumps(RESULTS_JSON_SCHEMA),
        ]

        stdout = self._run_process(args)

        try:
            envelope = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise MalformedResponseError(f"Claude CLI output was not valid JSON: {exc}") from exc

        if not isinstance(envelope, dict):
            raise MalformedResponseError("Claude CLI output was not a JSON object")

        if "structured_output" in envelope:
            raw = json.dumps(envelope["structured_output"])
        elif isinstance(envelope.get("result"), str):
            raw = envelope["result"]
        else:
            raise MalformedResponseError(
                "Claude CLI output is missing both 'structured_output' and a string 'result' field"
            )

        return parse_batch_response(raw, expected_count=len(transactions))


def connect() -> ClaudeCodeCategoriser:
    """Build a ClaudeCodeCategoriser using the `claude` CLI already on PATH."""
    return ClaudeCodeCategoriser()
