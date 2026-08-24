import subprocess
from typing import Callable

from categorisation.interface import BatchResult
from categorisation.prompt import build_prompt, parse_batch_response
from statement_export.parser import RawTransaction
from transaction_log.categories import Category


def _run_subprocess(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


class CodexCategoriser:
    """Categorises via Codex CLI's own non-interactive `codex exec` mode.

    Uses whatever auth Codex CLI is already configured with - no separate
    OpenAI API key or billing involved. `codex exec` prints only the final
    agent message to stdout (progress goes to stderr), so - unlike Claude's
    `-p --output-format json` - there's no envelope to unwrap here: the
    prompt asks for JSON directly, and stdout is parsed as-is.

    Not manually verified against a real Codex CLI install (unavailable in
    the environment this was built in) - verify once against a real `codex
    exec` before relying on it, per docs/agents/statement-export-pipeline.md.
    """

    def __init__(self, run_process: Callable[[list[str]], str] = _run_subprocess):
        self._run_process = run_process

    def categorise(self, transactions: list[RawTransaction], categories: list[Category]) -> BatchResult:
        prompt = build_prompt(transactions, categories)
        stdout = self._run_process(["codex", "exec", prompt])
        return parse_batch_response(stdout, expected_count=len(transactions))


def connect() -> CodexCategoriser:
    """Build a CodexCategoriser using the `codex` CLI already on PATH."""
    return CodexCategoriser()
