import os
from pathlib import Path

from categorisation.interface import Categoriser

REPO_ROOT = Path(__file__).resolve().parents[2]

BACKENDS = ("claude", "codex", "openai-compatible")


def connect() -> Categoriser:
    """Build the Categoriser configured via CATEGORISER_BACKEND in .env/the environment."""
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    backend = os.environ.get("CATEGORISER_BACKEND")

    if backend == "claude":
        from categorisation import claude_backend

        return claude_backend.connect()
    if backend == "codex":
        from categorisation import codex_backend

        return codex_backend.connect()
    if backend == "openai-compatible":
        from categorisation import openai_compatible_backend

        return openai_compatible_backend.connect()

    raise ValueError(
        f"CATEGORISER_BACKEND is {backend!r} - set it to one of {BACKENDS} in .env"
    )
