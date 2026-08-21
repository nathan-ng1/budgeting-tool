import pytest

from categorisation import factory
from categorisation.claude_backend import ClaudeCodeCategoriser
from categorisation.codex_backend import CodexCategoriser
from categorisation.openai_compatible_backend import OpenAICompatibleCategoriser

OPENAI_COMPATIBLE_ENV = {
    "CATEGORISER_BACKEND": "openai-compatible",
    "OPENAI_COMPATIBLE_BASE_URL": "http://localhost:11434/v1",
    "OPENAI_COMPATIBLE_MODEL": "llama3",
}


def test_claude_backend_selection():
    assert isinstance(factory.connect({"CATEGORISER_BACKEND": "claude"}), ClaudeCodeCategoriser)


def test_codex_backend_selection():
    assert isinstance(factory.connect({"CATEGORISER_BACKEND": "codex"}), CodexCategoriser)


def test_openai_compatible_backend_selection():
    assert isinstance(factory.connect(OPENAI_COMPATIBLE_ENV), OpenAICompatibleCategoriser)


def test_missing_backend_env_var_raises_a_clear_error():
    with pytest.raises(ValueError, match="CATEGORISER_BACKEND"):
        factory.connect({})


def test_unknown_backend_value_raises_a_clear_error():
    with pytest.raises(ValueError, match="not-a-real-backend"):
        factory.connect({"CATEGORISER_BACKEND": "not-a-real-backend"})


def test_an_openai_compatible_backend_missing_its_url_says_which_setting_is_missing():
    incomplete = {key: value for key, value in OPENAI_COMPATIBLE_ENV.items() if key != "OPENAI_COMPATIBLE_BASE_URL"}

    with pytest.raises(KeyError, match="OPENAI_COMPATIBLE_BASE_URL"):
        factory.connect(incomplete)


def test_connect_reads_the_ambient_configuration_when_given_none(monkeypatch):
    # The default path every real caller takes: no mapping passed, so the
    # configuration comes from .env plus the real environment.
    monkeypatch.setattr(factory.config, "load", lambda: {"CATEGORISER_BACKEND": "claude"})

    assert isinstance(factory.connect(), ClaudeCodeCategoriser)
