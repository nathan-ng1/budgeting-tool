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
            "groups": [],
        },
        {"version": "0.4.0", "date": "2026-10-04", "entries": ["Something older."], "groups": []},
    ]


def test_sub_headings_group_a_versions_bullets(serve, store, tmp_path):
    text = (
        "## v0.6.0 — 2026-10-16\n\n"
        "### New features\n\n- A feature.\n- Another feature.\n\n"
        "### Bug fixes\n\n- A fix.\n\n"
        "## v0.5.0 — 2026-10-15\n\n- Flat and older.\n"
    )

    assert history_from(serve, store, tmp_path, text) == [
        {
            "version": "0.6.0",
            "date": "2026-10-16",
            "entries": [],
            "groups": [
                {"title": "New features", "collaborator_only": False, "entries": ["A feature.", "Another feature."]},
                {"title": "Bug fixes", "collaborator_only": False, "entries": ["A fix."]},
            ],
        },
        {"version": "0.5.0", "date": "2026-10-15", "entries": ["Flat and older."], "groups": []},
    ]


def test_bullets_before_the_first_sub_heading_stay_ungrouped(serve, store, tmp_path):
    text = "## v0.6.0 — 2026-10-16\n\n- Loose.\n\n### Bug fixes\n\n- A fix.\n"

    [version] = history_from(serve, store, tmp_path, text)

    assert version["entries"] == ["Loose."]
    assert version["groups"] == [{"title": "Bug fixes", "collaborator_only": False, "entries": ["A fix."]}]


def test_the_collaborator_only_sub_heading_is_a_distinct_group(serve, store, tmp_path):
    text = (
        "## v0.6.0 — 2026-10-16\n\n"
        "### New features\n\n- A feature.\n\n"
        "### Collaborator Edition only\n\n- A pipeline change.\n"
    )

    [version] = history_from(serve, store, tmp_path, text)

    assert version["groups"] == [
        {"title": "New features", "collaborator_only": False, "entries": ["A feature."]},
        {"title": "Collaborator Edition only", "collaborator_only": True, "entries": ["A pipeline change."]},
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
        "### New features\n\n- A group before any version.\n",
        "## v0.4.1 — 2026-10-11\n\n### New features\n\nNo bullets under the group.\n",
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


def test_the_real_changelog_covers_every_release_back_to_the_first(running_server):
    """The backfill (Issue #194): dates are those of each GitHub Release."""
    _, body = get(running_server, "/api/version")

    assert [(v["version"], v["date"]) for v in body["history"]][-8:] == [
        ("0.4.0", "2026-10-11"),
        ("0.3.0", "2026-10-06"),
        ("0.2.0", "2026-10-04"),
        ("0.1.4", "2026-10-02"),
        ("0.1.3", "2026-09-06"),
        ("0.1.2", "2026-08-30"),
        ("0.1.1", "2026-08-28"),
        ("0.1.0", "2026-08-28"),
    ]
