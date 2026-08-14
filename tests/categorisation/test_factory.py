import pytest

from categorisation import factory
from categorisation.claude_backend import ClaudeCodeCategoriser
from categorisation.codex_backend import CodexCategoriser
from categorisation.openai_compatible_backend import OpenAICompatibleCategoriser


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in [
        "CATEGORISER_BACKEND",
        "OPENAI_COMPATIBLE_BASE_URL",
        "OPENAI_COMPATIBLE_API_KEY",
        "OPENAI_COMPATIBLE_MODEL",
    ]:
        monkeypatch.delenv(var, raising=False)
    yield
    for var in [
        "CATEGORISER_BACKEND",
        "OPENAI_COMPATIBLE_BASE_URL",
        "OPENAI_COMPATIBLE_API_KEY",
        "OPENAI_COMPATIBLE_MODEL",
    ]:
        monkeypatch.delenv(var, raising=False)


def test_claude_backend_selection(monkeypatch):
    monkeypatch.setenv("CATEGORISER_BACKEND", "claude")

    assert isinstance(factory.connect(), ClaudeCodeCategoriser)


def test_codex_backend_selection(monkeypatch):
    monkeypatch.setenv("CATEGORISER_BACKEND", "codex")

    assert isinstance(factory.connect(), CodexCategoriser)


def test_openai_compatible_backend_selection(monkeypatch):
    monkeypatch.setenv("CATEGORISER_BACKEND", "openai-compatible")
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("OPENAI_COMPATIBLE_MODEL", "llama3")

    assert isinstance(factory.connect(), OpenAICompatibleCategoriser)


def test_missing_backend_env_var_raises_a_clear_error():
    with pytest.raises(ValueError, match="CATEGORISER_BACKEND"):
        factory.connect()


def test_unknown_backend_value_raises_a_clear_error(monkeypatch):
    monkeypatch.setenv("CATEGORISER_BACKEND", "not-a-real-backend")

    with pytest.raises(ValueError, match="not-a-real-backend"):
        factory.connect()
