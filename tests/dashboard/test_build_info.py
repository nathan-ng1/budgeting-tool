"""`build_info.json`: the Version and Version History baked in at build time
(spec #236, decision S3, Issue #239), so a compiled build with no clone and no
package metadata still reports both - minus the Collaborator-only bullets.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

import pytest

from dashboard.build_info import write_build_info

SRC = Path(__file__).resolve().parents[2] / "src"

CHANGELOG = """\
# Changelog

## v0.7.0 — 2026-10-20

### New features

- A shared feature.

### Collaborator Edition only

- A pipeline change.

## v0.6.1 — 2026-10-18

### Collaborator Edition only

- Only Collaborators care.

## v0.6.0 — 2026-10-16

- Flat and older.
"""


@pytest.fixture
def changelog(tmp_path: Path) -> Path:
    path = tmp_path / "CHANGELOG.md"
    path.write_text(CHANGELOG, encoding="utf-8")
    return path


def get_version(server):
    with urlopen(f"http://127.0.0.1:{server.server_port}/api/version") as response:
        assert response.status == 200
        return json.loads(response.read())


def test_the_build_step_writes_the_version_and_the_history_without_collaborator_only_bullets(changelog, tmp_path):
    output = tmp_path / "build_info.json"

    write_build_info(changelog, output, version="0.7.0")

    info = json.loads(output.read_text(encoding="utf-8"))
    assert info["version"] == "0.7.0"
    assert info["history"] == [
        {
            "version": "0.7.0",
            "date": "2026-10-20",
            "entries": [],
            "groups": [{"title": "New features", "collaborator_only": False, "entries": ["A shared feature."]}],
        },
        {"version": "0.6.0", "date": "2026-10-16", "entries": ["Flat and older."], "groups": []},
    ]
    assert "Collaborator" not in output.read_text(encoding="utf-8")


def test_the_build_step_refuses_a_changelog_it_cannot_read(tmp_path):
    with pytest.raises(ValueError):
        write_build_info(tmp_path / "missing.md", tmp_path / "build_info.json", version="0.7.0")

    assert not (tmp_path / "build_info.json").exists()


def test_the_build_step_runs_as_a_module(changelog, tmp_path):
    output = tmp_path / "build_info.json"

    result = subprocess.run(
        [sys.executable, "-m", "dashboard.build_info", "--changelog", str(changelog), "--output", str(output)],
        env={**os.environ, "PYTHONPATH": str(SRC)},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text(encoding="utf-8"))["history"][0]["version"] == "0.7.0"


def test_the_apis_serve_from_build_info_when_it_is_present(serve, store, tmp_path):
    build_info = tmp_path / "build_info.json"
    build_info.write_text(
        json.dumps(
            {
                "version": "9.9.9",
                "history": [{"version": "9.9.9", "date": "2026-11-01", "entries": ["Baked in."], "groups": []}],
            }
        ),
        encoding="utf-8",
    )

    # The changelog path points nowhere: build_info.json alone is the source.
    server = serve(store, changelog_path=tmp_path / "nope.md", build_info_path=build_info)

    assert get_version(server) == {
        "version": "9.9.9",
        "history": [{"version": "9.9.9", "date": "2026-11-01", "entries": ["Baked in."], "groups": []}],
    }


def test_without_build_info_the_apis_behave_as_before(serve, store, changelog, tmp_path):
    from importlib.metadata import version as installed_version

    server = serve(store, changelog_path=changelog, build_info_path=tmp_path / "absent.json")

    body = get_version(server)
    assert body["version"] == installed_version("budgeting-tool")
    assert body["history"][0]["version"] == "0.7.0"
    assert body["history"][0]["groups"][-1]["collaborator_only"] is True


@pytest.mark.parametrize(
    "text",
    [
        "",
        "not json",
        "[]",
        '{"version": "0.7.0"}',
        '{"history": []}',
        '{"version": 7, "history": []}',
        '{"version": "0.7.0", "history": "nope"}',
        '{"version": "0.7.0", "history": [{"version": "0.7.0"}]}',
        '{"version": "0.7.0", "history": [{"version": "0.7.0", "date": "2026-10-20", "entries": [1], "groups": []}]}',
    ],
)
def test_a_malformed_build_info_degrades_to_unavailable_but_still_200(serve, store, changelog, tmp_path, text):
    build_info = tmp_path / "build_info.json"
    build_info.write_text(text, encoding="utf-8")

    server = serve(store, changelog_path=changelog, build_info_path=build_info)

    assert get_version(server) == {"version": None, "history": None}
