import subprocess
from typing import Callable

from advisor.interface import CategoryHistory, SuggestionResult
from advisor.prompt import build_prompt, parse_response


def _run_subprocess(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


class CodexAdvisor:
    """Generates a Budget Suggestion write-up via Codex CLI's own
    non-interactive `codex exec` mode - mirrors categorisation.codex_backend:
    `codex exec` prints only the final agent message to stdout (progress goes
    to stderr), and since the write-up is free text rather than a JSON
    contract, stdout is used as the write-up directly.

    Not manually verified against a real Codex CLI install (unavailable in
    the environment this was built in) - verify once against a real `codex
    exec` before relying on it, per docs/agents/statement-export-pipeline.md.
    """

    def __init__(self, run_process: Callable[[list[str]], str] = _run_subprocess):
        self._run_process = run_process

    def advise(self, history: list[CategoryHistory]) -> SuggestionResult:
        prompt = build_prompt(history)
        stdout = self._run_process(["codex", "exec", prompt])
        return parse_response(stdout)


def connect() -> CodexAdvisor:
    """Build a CodexAdvisor using the `codex` CLI already on PATH."""
    return CodexAdvisor()
