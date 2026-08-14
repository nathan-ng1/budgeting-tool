import os
import subprocess
from pathlib import Path
from typing import Callable

from categorisation.interface import BatchResult
from categorisation.prompt import build_prompt, parse_batch_response
from statement_export.parser import RawTransaction

REPO_ROOT = Path(__file__).resolve().parents[2]


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

    def __init__(self, run_process: Callable[[list[str]], str] = _run_subprocess, model: str | None = None):
        self._run_process = run_process
        self._model = model

    def categorise(self, transactions: list[RawTransaction], category_list: dict[str, set[str]]) -> BatchResult:
        prompt = build_prompt(transactions, category_list)
        args = ["codex", "exec", prompt]
        if self._model:
            args += ["--model", self._model]

        stdout = self._run_process(args)
        return parse_batch_response(stdout, expected_count=len(transactions))


def connect(model: str | None = None) -> CodexCategoriser:
    """Build a CodexCategoriser using the `codex` CLI already on PATH."""
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    return CodexCategoriser(model=model or os.environ.get("CODEX_CATEGORISER_MODEL"))
