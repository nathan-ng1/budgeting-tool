"""The Version endpoint (spec #191, Issue #192).

Exercised over real HTTP against a real LocalStore, so a test failing here
means the Dashboard's header would fail the same way.
"""

import json
from importlib.metadata import version as installed_version
from urllib.request import urlopen

import pytest


@pytest.fixture
def running_server(serve, store):
    return serve(store)


def get(server, path: str):
    with urlopen(f"http://127.0.0.1:{server.server_port}{path}") as response:
        return response.status, json.loads(response.read())


def test_the_version_is_the_installed_packages_and_history_is_not_yet_available(running_server):
    status, body = get(running_server, "/api/version")

    assert status == 200
    assert body == {"version": installed_version("budgeting-tool"), "history": None}
