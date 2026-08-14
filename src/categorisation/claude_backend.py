import json
import os
import subprocess
from pathlib import Path
from typing import Callable

from categorisation.interface import BatchResult, MalformedResponseError
from categorisation.prompt import build_prompt, parse_batch_response
from statement_export.parser import RawTransaction

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_subprocess(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


class ClaudeCodeCategoriser:
    """Categorises via Claude Code's own non-interactive `claude -p` mode.

    Uses whatever auth Claude Code is already configured with - no separate
    Anthropic API key or billing involved.
    """

    def __init__(self, run_process: Callable[[list[str]], str] = _run_subprocess, model: str | None = None):
        self._run_process = run_process
        self._model = model

    def categorise(self, transactions: list[RawTransaction], category_list: dict[str, set[str]]) -> BatchResult:
        prompt = build_prompt(transactions, category_list)
        args = ["claude", "-p", prompt, "--output-format", "json"]
        if self._model:
            args += ["--model", self._model]

        stdout = self._run_process(args)

        try:
            envelope = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise MalformedResponseError(f"Claude CLI output was not valid JSON: {exc}") from exc

        if not isinstance(envelope, dict) or not isinstance(envelope.get("result"), str):
            raise MalformedResponseError("Claude CLI output is missing a string 'result' field")

        return parse_batch_response(envelope["result"], expected_count=len(transactions))


def connect(model: str | None = None) -> ClaudeCodeCategoriser:
    """Build a ClaudeCodeCategoriser using the `claude` CLI already on PATH."""
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    return ClaudeCodeCategoriser(model=model or os.environ.get("CLAUDE_CATEGORISER_MODEL"))
