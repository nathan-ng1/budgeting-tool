"""The built Dashboard page is served by the same local server that serves the
Month Overview endpoint - see Issue #28 and ADR-0008 (nothing is hosted
off-machine).
"""

import socket
from http.client import HTTPConnection
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest


@pytest.fixture
def built_page(tmp_path: Path) -> Path:
    static_root = tmp_path / "static"
    (static_root / "assets").mkdir(parents=True)
    (static_root / "index.html").write_text("<!doctype html><title>Budgeting Dashboard</title>", encoding="utf-8")
    (static_root / "assets" / "index-abc123.js").write_text("console.log('dashboard')", encoding="utf-8")
    (static_root / "assets" / "index-abc123.css").write_text(".page{}", encoding="utf-8")
    return static_root


@pytest.fixture
def serving(serve, store, built_page: Path):
    return serve(store, static_root=built_page)


def get(server, path, timeout: float | None = None):
    # A timeout turns "the server never answers" into a failure rather than a
    # test run that hangs - see the idle-socket tests below.
    return urlopen(f"http://127.0.0.1:{server.server_port}{path}", timeout=timeout)


def test_the_root_path_serves_the_dashboard_page(serving):
    with get(serving, "/") as response:
        assert response.status == 200
        assert response.headers["Content-Type"] == "text/html; charset=utf-8"
        assert b"Budgeting Dashboard" in response.read()


def test_built_assets_are_served_with_the_content_type_the_browser_needs(serving):
    with get(serving, "/assets/index-abc123.js") as response:
        assert response.headers["Content-Type"] == "text/javascript"

    with get(serving, "/assets/index-abc123.css") as response:
        assert response.headers["Content-Type"] == "text/css"


def test_the_api_still_answers_alongside_the_page(serving):
    with get(serving, "/api/overview?year=2026&month=8") as response:
        assert response.status == 200
        assert response.headers["Content-Type"] == "application/json"


def test_a_missing_asset_is_a_404_rather_than_the_dashboard_page(serving):
    # A stale asset URL must not quietly return HTML - that surfaces as a
    # confusing MIME error in the browser instead of an obvious 404.
    with pytest.raises(HTTPError) as exc_info:
        get(serving, "/assets/does-not-exist.js")

    assert exc_info.value.code == 404


def test_an_unknown_path_is_a_404_because_there_is_no_client_side_router(serving):
    with pytest.raises(HTTPError) as exc_info:
        get(serving, "/transactions")

    assert exc_info.value.code == 404


@pytest.mark.parametrize("path", ["/../secret.txt", "/..%2fsecret.txt", "/assets/../../secret.txt"])
def test_a_path_escaping_the_static_root_is_refused(serving, tmp_path: Path, path: str):
    (tmp_path / "secret.txt").write_text("real financial figures", encoding="utf-8")

    # Sent raw rather than through urlopen, which would normalise the traversal
    # away before the server ever saw it.
    connection = HTTPConnection("127.0.0.1", serving.server_port)
    connection.putrequest("GET", path, skip_accept_encoding=True)
    connection.endheaders()
    response = connection.getresponse()
    body = response.read()
    connection.close()

    assert response.status == 403
    assert b"financial figures" not in body


def test_without_a_built_page_the_root_says_how_to_build_it(serve, store, tmp_path: Path):
    server = serve(store, static_root=tmp_path / "not-built")

    with pytest.raises(HTTPError) as exc_info:
        get(server, "/")

    assert exc_info.value.code == 501
    assert b"npm run build" in exc_info.value.read()


def test_an_idle_socket_does_not_stop_the_page_being_served(serving):
    # Browsers open speculative "preconnect" sockets and send nothing on them.
    # A server that handles one connection at a time blocks reading a request
    # line that never arrives, so index.html arrives but its JS and CSS never
    # do and the page renders blank - Issue #45.
    idle = socket.create_connection(("127.0.0.1", serving.server_port))
    try:
        with get(serving, "/assets/index-abc123.js", timeout=10) as response:
            assert response.status == 200
    finally:
        idle.close()


def test_several_idle_sockets_do_not_stop_the_api_answering(serving):
    # A real preconnect burst is more than one socket, and the API has to stay
    # reachable through it or the page renders with no data.
    idles = [socket.create_connection(("127.0.0.1", serving.server_port)) for _ in range(6)]
    try:
        with get(serving, "/api/overview?year=2026&month=8", timeout=10) as response:
            assert response.status == 200
    finally:
        for idle in idles:
            idle.close()
