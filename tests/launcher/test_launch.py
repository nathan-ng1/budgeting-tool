"""The Retail launcher's entry function (Issue #249, spec #236, decisions S4,
S10, S15, S16), driven with stand-ins for the browser, the port probe and the
running-instance check, so no real browser is opened.

`launch` blocks while it serves, so each test runs it on a thread and talks to
the real server it starts over HTTP.
"""

import json
import socket
import sqlite3
import threading
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, url2pathname, urlopen

import pytest

from database import location
from launcher import launch as launcher
from migration.runner import Migration, run_pending


def free_port() -> int:
    with closing(socket.socket()) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class Run:
    """One `launch` call on a background thread, with the opened URLs recorded."""

    def __init__(self, data_folder, **overrides):
        self.opened: list[str] = []
        self.opened_event = threading.Event()
        self.finished = threading.Event()
        self.error: BaseException | None = None
        self.data_folder = data_folder

        def open_browser(url):
            self.opened.append(url)
            self.opened_event.set()

        kwargs = {
            "data_folder": data_folder,
            "preferred_port": free_port(),
            "open_browser": open_browser,
            "port_is_free": lambda port: True,
            "instance_running": lambda port: False,
        }
        kwargs.update(overrides)
        self.kwargs = kwargs
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        try:
            launcher.launch(**self.kwargs)
        except BaseException as cause:  # surfaced by wait_until_finished
            self.error = cause
        finally:
            self.finished.set()

    def start(self):
        self.thread.start()
        return self

    def wait_until_open(self):
        assert self.opened_event.wait(10), "the browser was never opened"
        return self.opened[-1]

    def wait_until_finished(self):
        assert self.finished.wait(10), "launch did not return"
        if self.error is not None:
            raise self.error


@pytest.fixture
def data_folder(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()
    return folder


@pytest.fixture
def runs():
    started: list[Run] = []
    yield started
    for run in started:
        # Make sure no server outlives its test.
        port = launcher.read_instance(run.data_folder)
        if port is not None and not run.finished.is_set():
            try:
                post(port, "/api/quit")
            except OSError:
                pass
            run.finished.wait(10)


def start(runs, data_folder, **overrides) -> Run:
    run = Run(data_folder, **overrides).start()
    runs.append(run)
    return run


def get(port, path):
    with urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as response:
        return response.status, json.loads(response.read())


def post(port, path):
    request = Request(f"http://127.0.0.1:{port}{path}", method="POST", data=b"{}")
    with urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read())


def port_of(url: str) -> int:
    return int(url.rsplit(":", 1)[1].rstrip("/"))


def test_a_first_launch_starts_the_server_and_opens_the_browser_to_it(runs, data_folder):
    run = start(runs, data_folder)

    url = run.wait_until_open()

    assert url == f"http://127.0.0.1:{run.kwargs['preferred_port']}/"
    status, body = get(port_of(url), "/api/capabilities")
    assert status == 200
    assert set(body) == {"budget_suggestion", "statement_export"}


def test_a_first_launch_records_the_port_for_later_launches(runs, data_folder):
    run = start(runs, data_folder)

    port = port_of(run.wait_until_open())

    assert launcher.read_instance(data_folder) == port


def test_a_first_launch_keeps_the_database_in_the_resolved_data_location(runs, data_folder):
    run = start(runs, data_folder)
    port = port_of(run.wait_until_open())

    _, body = get(port, "/api/database")

    assert body["path"] == str((data_folder / location.DEFAULT_DATABASE_NAME).resolve())


def test_a_second_launch_reopens_the_running_instance_and_starts_no_second_server(runs, data_folder):
    first = start(runs, data_folder)
    port = port_of(first.wait_until_open())

    second = start(
        runs,
        data_folder,
        preferred_port=free_port(),
        instance_running=lambda candidate: candidate == port,
    )
    second.wait_until_finished()

    assert second.opened == [f"http://127.0.0.1:{port}/"]
    assert launcher.read_instance(data_folder) == port
    assert not first.finished.is_set()


def test_a_launch_that_finds_the_app_on_the_default_port_with_no_record_reuses_it(runs, data_folder):
    # e.g. a double-click right behind the first, before it has recorded its port.
    first = start(runs, data_folder)
    port = port_of(first.wait_until_open())
    launcher.clear_instance(data_folder)

    second = start(
        runs,
        data_folder,
        preferred_port=port,
        port_is_free=lambda candidate: candidate != port,
        instance_running=lambda candidate: candidate == port,
    )
    second.wait_until_finished()

    assert second.opened == [f"http://127.0.0.1:{port}/"]
    assert not first.finished.is_set()


def test_a_stale_record_of_a_dead_instance_is_replaced_by_a_fresh_start(runs, data_folder):
    launcher.write_instance(data_folder, 1)

    run = start(runs, data_folder)
    url = run.wait_until_open()

    assert port_of(url) == run.kwargs["preferred_port"]
    assert launcher.read_instance(data_folder) == port_of(url)


def test_a_taken_default_port_leads_to_the_next_free_port_which_is_recorded(runs, data_folder):
    preferred = free_port()
    run = start(runs, data_folder, preferred_port=preferred, port_is_free=lambda port: port != preferred)

    url = run.wait_until_open()

    assert port_of(url) == preferred + 1
    assert launcher.read_instance(data_folder) == preferred + 1
    status, _ = get(preferred + 1, "/api/capabilities")
    assert status == 200


def test_a_port_that_turns_out_to_be_taken_when_binding_is_skipped(runs, data_folder):
    # The probe says free, but something has the port by the time we bind.
    with closing(socket.socket()) as holder:
        holder.bind(("127.0.0.1", 0))
        holder.listen()
        preferred = holder.getsockname()[1]
        run = start(runs, data_folder, preferred_port=preferred)

        url = run.wait_until_open()

    assert port_of(url) != preferred


def test_quit_stops_the_server_and_clears_the_recorded_instance(runs, data_folder):
    run = start(runs, data_folder)
    port = port_of(run.wait_until_open())

    status, body = post(port, "/api/quit")
    run.wait_until_finished()

    assert (status, body) == (200, {"quitting": True})
    assert launcher.read_instance(data_folder) is None
    with pytest.raises(URLError):
        get(port, "/api/capabilities")


def test_after_quit_the_next_launch_starts_a_fresh_server(runs, data_folder):
    first = start(runs, data_folder)
    post(port_of(first.wait_until_open()), "/api/quit")
    first.wait_until_finished()

    second = start(runs, data_folder)
    port = port_of(second.wait_until_open())

    status, _ = get(port, "/api/capabilities")
    assert status == 200


def test_the_launched_dashboard_says_it_is_launcher_managed(runs, data_folder):
    run = start(runs, data_folder)
    port = port_of(run.wait_until_open())

    assert get(port, "/api/launcher") == (200, {"active": True, "update": None})


def test_the_real_port_probe_sees_a_listening_port_as_taken_and_a_free_one_as_free():
    with closing(socket.socket()) as holder:
        holder.bind(("127.0.0.1", 0))
        holder.listen()
        taken = holder.getsockname()[1]

        assert launcher.port_is_free(taken) is False

    assert launcher.port_is_free(taken) is True


def test_the_real_instance_check_recognises_a_running_launcher_instance_only(runs, data_folder):
    run = start(runs, data_folder)
    port = port_of(run.wait_until_open())

    assert launcher.instance_running(port) is True
    assert launcher.instance_running(free_port()) is False


def test_an_unreadable_instance_record_is_treated_as_no_instance(data_folder):
    (data_folder / launcher.INSTANCE_FILE_NAME).write_text("not json", encoding="utf-8")

    assert launcher.read_instance(data_folder) is None


# Migrate on launch (Issue #250, decision S8). Each Database below is a plain
# SQLite file at the resolved location, written before `launch` opens it.

OLD_INSTALL_SCHEMA = """
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL, name TEXT NOT NULL UNIQUE,
    emoji TEXT, locked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, amount REAL NOT NULL,
    type TEXT NOT NULL, category_id INTEGER NOT NULL REFERENCES categories(id), notes TEXT NOT NULL
);
INSERT INTO categories (type, name) VALUES ('Savings', 'Savings');
INSERT INTO transactions (date, amount, type, category_id, notes) VALUES ('2026-01-05', 10, 'Savings', 1, 'old');
"""


def database_path_in(data_folder):
    return data_folder / location.DEFAULT_DATABASE_NAME


def write_old_install(data_folder):
    path = database_path_in(data_folder)
    with closing(sqlite3.connect(path)) as connection:
        connection.executescript(OLD_INSTALL_SCHEMA)
    return path


def pre_migration_files(path):
    return sorted(path.parent.glob(f"{path.stem}.pre-migration-*{path.suffix}"))


def test_launching_with_pending_migrations_backs_up_migrates_then_starts_the_dashboard(runs, data_folder):
    path = write_old_install(data_folder)

    run = start(runs, data_folder)
    url = run.wait_until_open()

    assert url == f"http://127.0.0.1:{run.kwargs['preferred_port']}/"
    (backup,) = pre_migration_files(path)
    with closing(sqlite3.connect(backup)) as before:
        assert "goal_id" not in [row[1] for row in before.execute("PRAGMA table_info(transactions)")]
    with closing(sqlite3.connect(path)) as after:
        assert "goal_id" in [row[1] for row in after.execute("PRAGMA table_info(transactions)")]
        assert after.execute("SELECT notes FROM transactions").fetchall() == [("old",)]
    status, _ = get(port_of(url), "/api/transactions?year=2026&month=1")
    assert status == 200


def broken_migration(name="breaks"):
    def migrate(connection):
        connection.execute("DELETE FROM transactions")
        connection.commit()
        raise RuntimeError("boom")

    return Migration(name=name, migrate=migrate)


def test_a_failed_migration_restores_the_database_and_shows_the_error_instead_of_the_dashboard(runs, data_folder):
    path = write_old_install(data_folder)
    run = start(runs, data_folder, migrations=[broken_migration()])

    run.wait_until_finished()

    with closing(sqlite3.connect(path)) as restored:
        assert restored.execute("SELECT notes FROM transactions").fetchall() == [("old",)]
    assert pre_migration_files(path) == []
    (shown,) = run.opened
    assert shown.startswith("file:")
    page = Path(url2pathname(urlparse(shown).path)).read_text(encoding="utf-8")
    assert "breaks" in page
    assert "boom" in page
    assert "exactly as it was" in page
    assert launcher.read_instance(data_folder) is None


def test_a_database_from_a_newer_version_is_refused_with_the_error_shown(runs, data_folder):
    path = write_old_install(data_folder)
    with closing(sqlite3.connect(path)) as connection:
        run_pending(connection, [Migration("from_the_future", lambda c: None)])
    before = path.read_bytes()
    run = start(runs, data_folder)

    run.wait_until_finished()

    assert path.read_bytes() == before
    (shown,) = run.opened
    assert shown.startswith("file:")
    assert "newer version" in Path(url2pathname(urlparse(shown).path)).read_text(encoding="utf-8")
    assert launcher.read_instance(data_folder) is None


def test_the_error_page_escapes_what_it_shows(runs, data_folder):
    write_old_install(data_folder)
    failing = Migration("<script>x</script>", lambda c: (_ for _ in ()).throw(RuntimeError("<b>")))
    run = start(runs, data_folder, migrations=[failing])

    run.wait_until_finished()

    (shown,) = run.opened
    page = Path(url2pathname(urlparse(shown).path)).read_text(encoding="utf-8")
    assert "<script>x</script>" not in page
    assert "&lt;script&gt;" in page


def test_a_second_launch_never_migrates_underneath_a_running_instance(runs, data_folder):
    first = start(runs, data_folder)
    port = port_of(first.wait_until_open())
    path = database_path_in(data_folder)
    before = path.read_bytes()

    second = start(
        runs,
        data_folder,
        instance_running=lambda candidate: candidate == port,
        migrations=[broken_migration()],
    )
    second.wait_until_finished()

    assert second.opened == [f"http://127.0.0.1:{port}/"]
    assert path.read_bytes() == before
    assert pre_migration_files(path) == []


def test_a_good_launch_clears_the_error_page_an_earlier_failure_left(runs, data_folder):
    launcher.write_error_page(data_folder, "old problem")

    start(runs, data_folder).wait_until_open()

    assert not (data_folder / launcher.ERROR_PAGE_NAME).exists()


# The daily update check (Issue #251, decision S7). The launcher fetches the
# manifest and hands the answer to the Dashboard, which only reports it.

MANIFEST_URL = "https://updates.example/abc123/latest.json"
NOON = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)


class Manifest:
    def __init__(self, version="1.4.0", error: BaseException | None = None):
        self.version = version
        self.error = error
        self.requested: list[str] = []

    def __call__(self, url):
        self.requested.append(url)
        if self.error is not None:
            raise self.error
        return {"version": self.version}


def checking(manifest, *, installed="1.3.0", now=NOON):
    return {
        "update_manifest_url": MANIFEST_URL,
        "fetch_manifest": manifest,
        "installed_version": lambda: installed,
        "now": lambda: now,
    }


def launcher_state(run):
    return get(port_of(run.wait_until_open()), "/api/launcher")[1]


def test_a_newer_manifest_version_has_the_dashboard_report_an_update(runs, data_folder):
    manifest = Manifest("1.4.0")

    run = start(runs, data_folder, **checking(manifest))

    assert launcher_state(run) == {"active": True, "update": {"version": "1.4.0"}}
    assert manifest.requested == [MANIFEST_URL]


@pytest.mark.parametrize("published", ["1.3.0", "1.2.0"])
def test_an_equal_or_older_manifest_version_reports_no_update(runs, data_folder, published):
    run = start(runs, data_folder, **checking(Manifest(published)))

    assert launcher_state(run)["update"] is None


def test_a_launch_a_day_later_asks_again_and_one_within_the_day_does_not(runs, data_folder):
    manifest = Manifest("1.4.0")
    first = start(runs, data_folder, **checking(manifest))
    post(port_of(first.wait_until_open()), "/api/quit")
    first.wait_until_finished()

    same_day = start(runs, data_folder, **checking(manifest, now=NOON + timedelta(hours=23)))
    assert launcher_state(same_day)["update"] == {"version": "1.4.0"}
    post(port_of(same_day.wait_until_open()), "/api/quit")
    same_day.wait_until_finished()
    assert manifest.requested == [MANIFEST_URL]

    manifest.version = "1.5.0"
    next_day = start(runs, data_folder, **checking(manifest, now=NOON + timedelta(days=1)))

    assert launcher_state(next_day)["update"] == {"version": "1.5.0"}
    assert manifest.requested == [MANIFEST_URL, MANIFEST_URL]


def test_a_failed_fetch_still_opens_the_dashboard_with_no_update(runs, data_folder):
    run = start(runs, data_folder, **checking(Manifest(error=OSError("offline"))))

    assert launcher_state(run) == {"active": True, "update": None}
    assert run.error is None


def test_reopening_a_running_instance_makes_no_request(runs, data_folder):
    first = start(runs, data_folder)
    port = port_of(first.wait_until_open())
    manifest = Manifest()

    second = start(
        runs, data_folder, instance_running=lambda candidate: candidate == port, **checking(manifest)
    )
    second.wait_until_finished()

    assert manifest.requested == []


def test_with_no_manifest_address_configured_nothing_is_requested(runs, data_folder):
    manifest = Manifest()

    run = start(runs, data_folder, fetch_manifest=manifest, installed_version=lambda: "1.3.0")

    assert launcher_state(run)["update"] is None
    assert manifest.requested == []


def test_the_dashboard_serving_an_update_banner_connects_to_nothing_but_this_machine(runs, data_folder, monkeypatch):
    destinations = []
    real_connect, real_connect_ex = socket.socket.connect, socket.socket.connect_ex

    def recording_connect(self, address):
        destinations.append(address)
        return real_connect(self, address)

    def recording_connect_ex(self, address):
        destinations.append(address)
        return real_connect_ex(self, address)

    monkeypatch.setattr(socket.socket, "connect", recording_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", recording_connect_ex)
    run = start(runs, data_folder, **checking(Manifest("1.4.0")))
    port = port_of(run.wait_until_open())

    for path in ("/api/launcher", "/api/version", "/api/capabilities", "/api/settings"):
        get(port, path)

    assert destinations, "the requests above should have been recorded"
    assert {address[0] for address in destinations} == {"127.0.0.1"}
