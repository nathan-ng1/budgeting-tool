"""The launcher's daily update check (Issue #251, spec #236, decision S7), driven
with a stand-in fetch and clock so nothing touches the network and no real day
has to pass.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

from launcher import update_check

URL = "https://updates.example/abc123/latest.json"
START = datetime(2026, 10, 17, 9, 0, tzinfo=timezone.utc)


class Fetcher:
    """A manifest source that records every request it is asked for."""

    def __init__(self, manifest=None, error: BaseException | None = None):
        self.manifest = {"version": "1.4.0"} if manifest is None else manifest
        self.error = error
        self.requested: list[str] = []

    def __call__(self, url):
        self.requested.append(url)
        if self.error is not None:
            raise self.error
        return self.manifest


def check(data_folder, fetch, *, installed="1.3.0", now=START, url=URL):
    return update_check.check_for_update(
        data_folder, installed_version=installed, manifest_url=url, fetch=fetch, now=lambda: now
    )


def test_a_newer_manifest_version_is_reported(tmp_path):
    assert check(tmp_path, Fetcher({"version": "1.4.0"})) == "1.4.0"


def test_the_same_version_is_not_reported(tmp_path):
    assert check(tmp_path, Fetcher({"version": "1.3.0"})) is None


def test_an_older_version_is_not_reported(tmp_path):
    assert check(tmp_path, Fetcher({"version": "1.2.9"})) is None


def test_a_leading_v_in_the_manifest_is_understood(tmp_path):
    assert check(tmp_path, Fetcher({"version": "v1.4.0"})) == "1.4.0"


def test_versions_compare_numerically_not_alphabetically(tmp_path):
    assert check(tmp_path, Fetcher({"version": "1.10.0"}), installed="1.9.0") == "1.10.0"


def test_a_second_check_within_a_day_makes_no_new_request(tmp_path):
    fetch = Fetcher()
    check(tmp_path, fetch)

    again = check(tmp_path, fetch, now=START + timedelta(hours=23, minutes=59))

    assert fetch.requested == [URL]
    assert again == "1.4.0"


def test_a_check_after_a_day_requests_again(tmp_path):
    fetch = Fetcher({"version": "1.4.0"})
    check(tmp_path, fetch)
    fetch.manifest = {"version": "1.5.0"}

    later = check(tmp_path, fetch, now=START + timedelta(days=1))

    assert fetch.requested == [URL, URL]
    assert later == "1.5.0"


def test_the_remembered_answer_follows_the_installed_version(tmp_path):
    # Updated between two launches in the same day: no new request, no stale banner.
    fetch = Fetcher({"version": "1.4.0"})
    check(tmp_path, fetch)

    assert check(tmp_path, fetch, installed="1.4.0", now=START + timedelta(hours=1)) is None
    assert fetch.requested == [URL]


@pytest.mark.parametrize(
    "error",
    [
        OSError("offline"),
        TimeoutError("slow"),
        ValueError("not json"),
        RuntimeError("anything else"),
    ],
)
def test_a_failed_fetch_shows_nothing_and_does_not_raise(tmp_path, error):
    assert check(tmp_path, Fetcher(error=error)) is None


@pytest.mark.parametrize(
    "manifest",
    [
        None,
        [],
        "1.4.0",
        {},
        {"version": None},
        {"version": 140},
        {"version": ""},
        {"version": "next"},
        {"version": "1.4.0-beta"},
    ],
)
def test_a_malformed_manifest_shows_nothing_and_does_not_raise(tmp_path, manifest):
    fetch = Fetcher()
    fetch.manifest = manifest

    assert check(tmp_path, fetch) is None


def test_a_failed_check_still_counts_as_the_days_check(tmp_path):
    # Offline, every launch would otherwise retry and wait on the network.
    fetch = Fetcher(error=OSError("offline"))
    check(tmp_path, fetch)

    check(tmp_path, fetch, now=START + timedelta(hours=1))

    assert len(fetch.requested) == 1


def test_a_failed_check_keeps_the_update_already_known(tmp_path):
    check(tmp_path, Fetcher({"version": "1.4.0"}))

    after_failure = check(tmp_path, Fetcher(error=OSError("offline")), now=START + timedelta(days=1))

    assert after_failure == "1.4.0"


def test_a_malformed_manifest_keeps_the_update_already_known(tmp_path):
    check(tmp_path, Fetcher({"version": "1.4.0"}))

    after_bad = check(tmp_path, Fetcher({"nonsense": True}), now=START + timedelta(days=1))

    assert after_bad == "1.4.0"


def test_an_unreadable_record_of_the_last_check_means_check_now(tmp_path):
    (tmp_path / update_check.STATE_FILE_NAME).write_text("not json", encoding="utf-8")
    fetch = Fetcher()

    assert check(tmp_path, fetch) == "1.4.0"
    assert fetch.requested == [URL]


@pytest.mark.parametrize(
    "state",
    [
        {"checked_at": "yesterday", "latest_version": "9.9.9"},
        {"checked_at": 5, "latest_version": "9.9.9"},
        {"latest_version": "9.9.9"},
        [],
    ],
)
def test_a_record_of_the_wrong_shape_means_check_now(tmp_path, state):
    (tmp_path / update_check.STATE_FILE_NAME).write_text(json.dumps(state), encoding="utf-8")
    fetch = Fetcher({"version": "1.4.0"})

    assert check(tmp_path, fetch) == "1.4.0"
    assert fetch.requested == [URL]


def test_a_clock_set_back_does_not_silence_the_check_until_it_catches_up(tmp_path):
    fetch = Fetcher()
    check(tmp_path, fetch, now=START)

    check(tmp_path, fetch, now=START - timedelta(days=30))

    assert len(fetch.requested) == 2


def test_a_record_written_without_a_timezone_is_still_read(tmp_path):
    (tmp_path / update_check.STATE_FILE_NAME).write_text(
        json.dumps({"checked_at": "2026-10-17T08:00:00", "latest_version": "1.4.0"}), encoding="utf-8"
    )
    fetch = Fetcher()

    assert check(tmp_path, fetch) == "1.4.0"
    assert fetch.requested == []


def test_no_manifest_address_means_no_request_and_no_banner(tmp_path):
    fetch = Fetcher()

    assert check(tmp_path, fetch, url=None) is None
    assert fetch.requested == []


def test_an_unknown_installed_version_means_no_request_and_no_banner(tmp_path):
    fetch = Fetcher()

    assert check(tmp_path, fetch, installed=None) is None
    assert fetch.requested == []


def test_a_data_folder_that_cannot_be_written_does_not_stop_the_check(tmp_path):
    not_a_folder = tmp_path / "file"
    not_a_folder.write_text("x", encoding="utf-8")

    assert check(not_a_folder, Fetcher()) == "1.4.0"


# The real fetch, against a local server standing in for the update host.


@pytest.fixture
def host():
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread

    body = {"bytes": b'{"version": "1.4.0", "history": []}'}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Length", str(len(body["bytes"])))
            self.end_headers()
            self.wfile.write(body["bytes"])

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    yield body, f"http://127.0.0.1:{server.server_port}/latest.json"
    server.shutdown()
    server.server_close()


def test_the_real_fetch_reads_and_parses_the_manifest(tmp_path, host):
    _, url = host

    assert check(tmp_path, update_check.fetch_manifest, url=url) == "1.4.0"


def test_the_real_fetch_of_something_that_is_not_json_shows_nothing(tmp_path, host):
    body, url = host
    body["bytes"] = b"<html>an error page</html>"

    assert check(tmp_path, update_check.fetch_manifest, url=url) is None


def test_the_real_fetch_of_an_address_nothing_answers_shows_nothing(tmp_path):
    assert check(tmp_path, update_check.fetch_manifest, url="http://127.0.0.1:1/latest.json") is None
