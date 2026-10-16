"""A Dashboard run outside the launcher (the Collaborator Edition) has no Quit
and no startup notice: both belong to the Retail launcher (Issue #249)."""

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def request(server, method, path, headers=None):
    http_request = Request(
        f"http://127.0.0.1:{server.server_port}{path}",
        method=method,
        data=b"{}" if method == "POST" else None,
        headers=headers or {},
    )
    try:
        with urlopen(http_request) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read())


def test_a_dashboard_run_directly_reports_the_launcher_inactive(serve, store):
    server = serve(store)

    assert request(server, "GET", "/api/launcher") == (200, {"active": False})


def test_a_dashboard_run_directly_has_no_quit(serve, store):
    server = serve(store)

    status, _ = request(server, "POST", "/api/quit")

    assert status == 404


def test_quit_asks_the_launcher_to_stop_and_says_so(serve, store):
    quits = []
    server = serve(store, on_quit=lambda: quits.append("quit"))

    assert request(server, "GET", "/api/launcher") == (200, {"active": True})
    assert request(server, "POST", "/api/quit") == (200, {"quitting": True})
    assert quits == ["quit"]


def test_quit_refuses_a_request_from_another_sites_page(serve, store):
    quits = []
    server = serve(store, on_quit=lambda: quits.append("quit"))

    status, _ = request(server, "POST", "/api/quit", headers={"Origin": "https://evil.example"})

    assert status == 403
    assert quits == []


def test_quit_accepts_a_request_from_the_dashboards_own_page(serve, store):
    quits = []
    server = serve(store, on_quit=lambda: quits.append("quit"))

    status, _ = request(
        server, "POST", "/api/quit", headers={"Origin": f"http://127.0.0.1:{server.server_port}"}
    )

    assert status == 200
    assert quits == ["quit"]
