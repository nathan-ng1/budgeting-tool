"""The one Database-location resolver every entry point uses (Issue #238, ADR-0032)."""

from pathlib import Path

import pytest

from database import location
from database.location import (
    POINTER_FILE_NAME,
    SOURCE_DEFAULT,
    SOURCE_OVERRIDE,
    SOURCE_POINTER,
    default_data_folder,
    resolve_database_path,
    resolve_location,
    write_pointer,
)


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    path = tmp_path / "user-data"
    path.mkdir()
    return path


@pytest.fixture
def env_file(tmp_path: Path) -> Path:
    return tmp_path / ".env"


def resolve(env_file: Path, folder: Path, environ: dict[str, str] | None = None):
    return resolve_location(env_path=env_file, data_folder=folder, environ=environ or {})


def test_the_environment_variable_wins_over_everything_else(tmp_path, env_file, folder):
    env_file.write_text("DATABASE_PATH=from-dotenv.db\n", encoding="utf-8")
    (folder / POINTER_FILE_NAME).write_text(str(tmp_path / "pointed.db"), encoding="utf-8")

    found = resolve(env_file, folder, {"DATABASE_PATH": "from-environment.db"})

    assert found.path == Path("from-environment.db")
    assert found.source == SOURCE_OVERRIDE


def test_a_dotenv_value_wins_over_the_pointer_file_and_the_default(tmp_path, env_file, folder):
    env_file.write_text("# mine\nDATABASE_PATH= .data/budget.db\n", encoding="utf-8")
    (folder / POINTER_FILE_NAME).write_text(str(tmp_path / "pointed.db"), encoding="utf-8")

    found = resolve(env_file, folder)

    assert found.path == Path(".data/budget.db")
    assert found.source == SOURCE_OVERRIDE


def test_nothing_else_is_consulted_when_an_override_is_set(env_file, folder):
    env_file.write_text("DATABASE_PATH=mine.db\n", encoding="utf-8")
    (folder / POINTER_FILE_NAME).write_bytes(b"\xff\xfe not text \x00")

    assert resolve(env_file, folder).path == Path("mine.db")


def test_a_blank_override_counts_as_unset(env_file, folder):
    env_file.write_text("DATABASE_PATH=\n", encoding="utf-8")

    assert resolve(env_file, folder, {"DATABASE_PATH": "  "}).source == SOURCE_DEFAULT


def test_the_pointer_file_is_used_when_there_is_no_override(tmp_path, env_file, folder):
    elsewhere = tmp_path / "Dropbox"
    elsewhere.mkdir()
    write_pointer(folder, elsewhere / "budget.db")

    found = resolve(env_file, folder)

    assert found.path == elsewhere / "budget.db"
    assert found.source == SOURCE_POINTER


def test_a_pointer_to_a_database_that_is_not_there_yet_is_still_followed(tmp_path, env_file, folder):
    write_pointer(folder, tmp_path / "budget.db")

    assert resolve(env_file, folder).source == SOURCE_POINTER


def test_with_neither_the_default_folder_holds_the_database(env_file, folder):
    found = resolve(env_file, folder)

    assert found.path == folder / "budget.db"
    assert found.source == SOURCE_DEFAULT


def test_a_missing_dotenv_is_not_an_error(tmp_path, folder):
    assert resolve(tmp_path / "no" / ".env", folder).source == SOURCE_DEFAULT


@pytest.mark.parametrize(
    "contents",
    [
        b"",
        b"   \n",
        b"relative/budget.db",
        b"\xff\xfe\x00 not utf-8",
    ],
    ids=["empty", "blank", "relative", "undecodable"],
)
def test_an_invalid_pointer_falls_back_to_the_default_folder(env_file, folder, contents):
    (folder / POINTER_FILE_NAME).write_bytes(contents)

    found = resolve(env_file, folder)

    assert found.path == folder / "budget.db"
    assert found.source == SOURCE_DEFAULT


def test_a_pointer_to_a_folder_or_a_folder_that_is_gone_falls_back(tmp_path, env_file, folder):
    write_pointer(folder, tmp_path)  # a directory, not a file
    assert resolve(env_file, folder).source == SOURCE_DEFAULT

    write_pointer(folder, tmp_path / "unplugged-drive" / "budget.db")
    assert resolve(env_file, folder).source == SOURCE_DEFAULT


def test_an_unreadable_pointer_falls_back(env_file, folder, monkeypatch):
    (folder / POINTER_FILE_NAME).write_text("whatever", encoding="utf-8")

    def locked(self, *args, **kwargs):
        raise PermissionError("locked")

    monkeypatch.setattr(Path, "read_text", locked)

    assert resolve(env_file, folder).source == SOURCE_DEFAULT


def test_writing_the_pointer_creates_the_data_folder_and_replaces_an_older_pointer(tmp_path):
    folder = tmp_path / "not" / "yet"

    write_pointer(folder, tmp_path / "one.db")
    write_pointer(folder, tmp_path / "two.db")

    assert (folder / POINTER_FILE_NAME).read_text(encoding="utf-8").strip() == str(tmp_path / "two.db")
    assert [p.name for p in folder.iterdir()] == [POINTER_FILE_NAME]


def test_a_failed_pointer_write_leaves_the_old_pointer_and_no_stray_file(tmp_path, monkeypatch):
    folder = tmp_path / "data"
    write_pointer(folder, tmp_path / "one.db")

    def cannot_replace(source, target):
        raise PermissionError("denied")

    monkeypatch.setattr(location.os, "replace", cannot_replace)

    with pytest.raises(OSError):
        write_pointer(folder, tmp_path / "two.db")

    assert (folder / POINTER_FILE_NAME).read_text(encoding="utf-8").strip() == str(tmp_path / "one.db")
    assert [p.name for p in folder.iterdir()] == [POINTER_FILE_NAME]


def test_resolve_database_path_returns_an_explicit_path_untouched(tmp_path):
    assert resolve_database_path(tmp_path / "given.db") == tmp_path / "given.db"


def test_resolve_database_path_without_an_argument_follows_the_resolver(env_file, folder):
    env_file.write_text("DATABASE_PATH=mine.db\n", encoding="utf-8")

    assert resolve_database_path(env_path=env_file, data_folder=folder, environ={}) == Path("mine.db")


@pytest.mark.parametrize(
    ("platform", "environ", "expected"),
    [
        ("win32", {"LOCALAPPDATA": "C:/Users/me/AppData/Local"}, Path("C:/Users/me/AppData/Local/Budgeting Tool")),
        ("darwin", {}, Path("/Users/me/Library/Application Support/Budgeting Tool")),
        ("linux", {}, Path("/Users/me/.local/share/Budgeting Tool")),
        ("linux", {"XDG_DATA_HOME": "/xdg"}, Path("/xdg/Budgeting Tool")),
    ],
)
def test_the_default_data_folder_is_per_user_and_per_platform(platform, environ, expected):
    assert default_data_folder(platform=platform, environ=environ, home=Path("/Users/me")) == expected


def test_windows_without_local_app_data_falls_back_under_the_home_folder():
    found = default_data_folder(platform="win32", environ={}, home=Path("/Users/me"))

    assert found == Path("/Users/me/AppData/Local/Budgeting Tool")
