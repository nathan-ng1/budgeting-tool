"""Where categorisation's configuration comes from - see Issue #30.

These are the only tests that touch a `.env` file at all, and they point at a
tmp_path one rather than the repo's own, so they say the same thing on a
configured dev machine as on a clean CI checkout.
"""

from pathlib import Path

from categorisation import config


def write_env(root: Path, body: str) -> Path:
    (root / ".env").write_text(body, encoding="utf-8")
    return root


def test_reads_settings_from_the_repo_root_env_file(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config, "REPO_ROOT", write_env(tmp_path, "CATEGORISER_BACKEND=codex\n"))

    assert config.load()["CATEGORISER_BACKEND"] == "codex"


def test_a_real_environment_variable_wins_over_the_env_file(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config, "REPO_ROOT", write_env(tmp_path, "CATEGORISER_BACKEND=codex\n"))
    monkeypatch.setenv("CATEGORISER_BACKEND", "claude")

    assert config.load()["CATEGORISER_BACKEND"] == "claude"


def test_a_missing_env_file_is_not_an_error(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config, "REPO_ROOT", tmp_path)
    monkeypatch.delenv("CATEGORISER_BACKEND", raising=False)

    assert "CATEGORISER_BACKEND" not in config.load()


def test_loading_does_not_leak_env_file_settings_into_the_process(tmp_path: Path, monkeypatch):
    # dotenv's load_dotenv mutates os.environ, which is what made this config
    # impossible to test around in the first place (Issue #30).
    import os

    monkeypatch.setattr(config, "REPO_ROOT", write_env(tmp_path, "A_SETTING_NOBODY_ELSE_SETS=1\n"))

    config.load()

    assert "A_SETTING_NOBODY_ELSE_SETS" not in os.environ
