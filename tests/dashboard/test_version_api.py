"""The Version endpoint (spec #191, Issues #192 and #193).

Exercised over real HTTP against a real LocalStore, so a test failing here
means the Dashboard's header would fail the same way.
"""

import json
from importlib.metadata import version as installed_version
from pathlib import Path
from urllib.request import urlopen

import pytest

from dashboard.server import CHANGELOG_PATH

WELL_FORMED = """\
# Changelog

## v0.4.1 — 2026-10-11

- Updating no longer stops on a stray file.
- Second change.

## v0.4.0 — 2026-10-04

- Something older.
"""


@pytest.fixture
def running_server(serve, store):
    return serve(store)


def get(server, path: str):
    with urlopen(f"http://127.0.0.1:{server.server_port}{path}") as response:
        return response.status, json.loads(response.read())


def history_from(serve, store, tmp_path: Path, text: str | None):
    changelog = tmp_path / "CHANGELOG.md"
    if text is not None:
        changelog.write_text(text, encoding="utf-8")
    status, body = get(serve(store, changelog_path=changelog), "/api/version")
    assert status == 200
    return body["history"]


def test_the_version_is_the_installed_packages(running_server):
    status, body = get(running_server, "/api/version")

    assert status == 200
    assert body["version"] == installed_version("budgeting-tool")


def test_the_history_is_the_changelog_parsed_newest_first(serve, store, tmp_path):
    assert history_from(serve, store, tmp_path, WELL_FORMED) == [
        {
            "version": "0.4.1",
            "date": "2026-10-11",
            "entries": ["Updating no longer stops on a stray file.", "Second change."],
        },
        {"version": "0.4.0", "date": "2026-10-04", "entries": ["Something older."]},
    ]


def test_a_missing_changelog_gives_no_history_but_still_200(serve, store, tmp_path):
    assert history_from(serve, store, tmp_path, None) is None


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Just some prose, no versions.\n",
        "## v0.4.1 - not a date\n\n- A change.\n",
        "## v0.4.1 — 2026-10-11\n\nNo bullets here.\n",
        "## 0.4.1 — 2026-10-11\n\n- Missing the v.\n",
    ],
)
def test_a_malformed_changelog_gives_no_history_but_still_200(serve, store, tmp_path, text):
    assert history_from(serve, store, tmp_path, text) is None


def test_the_real_changelog_leads_with_the_released_version(running_server):
    """The release invariant (ADR-0029): a release can't ship without its entry."""
    _, body = get(running_server, "/api/version")

    assert CHANGELOG_PATH.is_file()
    assert body["history"] is not None
    assert body["history"][0]["version"] == body["version"]
