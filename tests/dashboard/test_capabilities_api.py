"""The capabilities endpoint (spec #236, Issue #248, decision S14).

The Dashboard reports which Collaborator-only features exist in this build, so
the frontend asks rather than checking an edition name. Here the Collaborator-only
packages are importable (the repo checkout), so every capability is present; the
Retail-shaped run in test_retail_shape.py covers them being absent.
"""

import json
from urllib.request import urlopen

import pytest


@pytest.fixture
def running_server(serve, store):
    return serve(store)


def get(server, path: str):
    with urlopen(f"http://127.0.0.1:{server.server_port}{path}") as response:
        return response.status, json.loads(response.read())


def test_every_collaborator_only_feature_is_reported_present_when_its_package_ships(running_server):
    status, body = get(running_server, "/api/capabilities")

    assert status == 200
    assert body == {"budget_suggestion": True, "statement_export": True}


def test_the_budget_suggestion_endpoint_is_served_when_its_capability_is_present(running_server):
    status, _body = get(running_server, "/api/budget-suggestion")

    assert status == 200
