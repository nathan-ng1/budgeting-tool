import pytest

from advisor import factory
from advisor.claude_backend import ClaudeCodeAdvisor
from advisor.codex_backend import CodexAdvisor
from advisor.openai_compatible_backend import OpenAICompatibleAdvisor

OPENAI_COMPATIBLE_ENV = {
    "ADVISOR_BACKEND": "openai-compatible",
    "ADVISOR_OPENAI_COMPATIBLE_BASE_URL": "http://localhost:11434/v1",
    "ADVISOR_OPENAI_COMPATIBLE_MODEL": "llama3",
}


def test_claude_backend_selection():
    assert isinstance(factory.connect({"ADVISOR_BACKEND": "claude"}), ClaudeCodeAdvisor)


def test_codex_backend_selection():
    assert isinstance(factory.connect({"ADVISOR_BACKEND": "codex"}), CodexAdvisor)


def test_openai_compatible_backend_selection():
    assert isinstance(factory.connect(OPENAI_COMPATIBLE_ENV), OpenAICompatibleAdvisor)


def test_missing_backend_env_var_raises_a_clear_error():
    with pytest.raises(ValueError, match="ADVISOR_BACKEND"):
        factory.connect({})


def test_unknown_backend_value_raises_a_clear_error():
    with pytest.raises(ValueError, match="not-a-real-backend"):
        factory.connect({"ADVISOR_BACKEND": "not-a-real-backend"})


def test_an_openai_compatible_backend_missing_its_url_says_which_setting_is_missing():
    incomplete = {k: v for k, v in OPENAI_COMPATIBLE_ENV.items() if k != "ADVISOR_OPENAI_COMPATIBLE_BASE_URL"}

    with pytest.raises(KeyError, match="ADVISOR_OPENAI_COMPATIBLE_BASE_URL"):
        factory.connect(incomplete)


def test_connect_reads_the_ambient_configuration_when_given_none(monkeypatch):
    monkeypatch.setattr(factory.config, "load", lambda: {"ADVISOR_BACKEND": "claude"})

    assert isinstance(factory.connect(), ClaudeCodeAdvisor)


def test_advisor_backend_is_independent_of_categoriser_backend():
    # CATEGORISER_BACKEND being set to something else/invalid must not affect
    # ADVISOR_BACKEND selection - ADR-0014's two settings are independent.
    env = {"CATEGORISER_BACKEND": "not-a-real-backend", "ADVISOR_BACKEND": "claude"}

    assert isinstance(factory.connect(env), ClaudeCodeAdvisor)
