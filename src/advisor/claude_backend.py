import json
import subprocess
from typing import Callable

from advisor.interface import CategoryHistory, MalformedResponseError, SuggestionResult
from advisor.prompt import build_prompt, parse_response


def _run_subprocess(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


class ClaudeCodeAdvisor:
    """Generates a Budget Suggestion write-up via Claude Code's own
    non-interactive `claude -p` mode - mirrors categorisation.claude_backend
    exactly, minus --json-schema: the write-up is free text, not a
    structured contract, so only --output-format json is needed to reliably
    unwrap the envelope's `result` field.
    """

    def __init__(self, run_process: Callable[[list[str]], str] = _run_subprocess):
        self._run_process = run_process

    def advise(self, history: list[CategoryHistory]) -> SuggestionResult:
        prompt = build_prompt(history)
        args = ["claude", "-p", prompt, "--output-format", "json"]

        stdout = self._run_process(args)

        try:
            envelope = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise MalformedResponseError(f"Claude CLI output was not valid JSON: {exc}") from exc

        if not isinstance(envelope, dict) or not isinstance(envelope.get("result"), str):
            raise MalformedResponseError("Claude CLI output is missing a string 'result' field")

        return parse_response(envelope["result"])


def connect() -> ClaudeCodeAdvisor:
    """Build a ClaudeCodeAdvisor using the `claude` CLI already on PATH."""
    return ClaudeCodeAdvisor()
