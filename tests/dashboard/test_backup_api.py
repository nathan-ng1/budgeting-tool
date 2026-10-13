"""Downloading a Backup of the Database and the "Last backed up" line
(Issue #197, ADR-0030). Exercised over real HTTP against real Databases."""

import json
import sqlite3
import threading
from contextlib import closing
from pathlib import Path
from urllib.request import urlopen

from dashboard.server import build_server
from database.store import connect, open_connection
from migration.registry import MIGRATIONS
from migration.runner import pending


def get(server, path: str):
    with urlopen(f"http://127.0.0.1:{server.server_port}{path}") as response:
        return response.status, response.headers, response.read()


def database_info(server) -> dict:
    return json.loads(get(server, "/api/database")[2])


def test_the_downloaded_backup_opens_as_a_database_with_the_same_rows(serve, store, make_candidate, tmp_path: Path):
    store.append_rows([make_candidate(notes="coffee"), make_candidate(notes="lunch")])
    server = serve(store)

    status, headers, body = get(server, "/api/database/backup")

    assert status == 200
    assert headers["Content-Disposition"].startswith('attachment; filename="budget-backup-')
    assert headers["Content-Disposition"].endswith('.db"')
    downloaded = tmp_path / "downloaded.db"
    downloaded.write_bytes(body)
    with closing(sqlite3.connect(downloaded)) as connection:
        notes = sorted(row[0] for row in connection.execute("SELECT notes FROM transactions"))
    assert notes == ["coffee", "lunch"]


def test_the_backup_is_recognised_as_an_up_to_date_database(serve, store, tmp_path: Path):
    server = serve(store)

    downloaded = tmp_path / "downloaded.db"
    downloaded.write_bytes(get(server, "/api/database/backup")[2])

    with closing(sqlite3.connect(downloaded)) as connection:
        assert pending(connection, MIGRATIONS) == []
    open_connection(downloaded).close()  # usable as the Dashboard's own Database


def test_the_backup_is_taken_from_a_live_database_without_disturbing_it(serve, store, make_candidate):
    server = serve(store)
    store.append_rows([make_candidate(notes="before")])

    get(server, "/api/database/backup")
    store.append_rows([make_candidate(notes="after")])

    assert len(store.read_existing_rows()) == 2


def test_last_backed_up_is_never_on_a_fresh_install_then_the_time_of_the_latest_backup(serve, store):
    server = serve(store)
    assert database_info(server)["last_backed_up"] is None

    get(server, "/api/database/backup")

    stamp = database_info(server)["last_backed_up"]
    assert stamp is not None
    assert stamp.startswith("20")  # an ISO timestamp


def test_last_backed_up_survives_a_dashboard_restart(tmp_path: Path):
    def run(store):
        server = build_server(store)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread

    def stop(server, thread):
        server.shutdown()
        thread.join()
        server.server_close()

    first = connect(tmp_path / "budget.db")
    server, thread = run(first)
    get(server, "/api/database/backup")
    stamp = database_info(server)["last_backed_up"]
    stop(server, thread)
    first.close()

    server, thread = run(connect(tmp_path / "budget.db"))
    try:
        assert database_info(server)["last_backed_up"] == stamp
    finally:
        stop(server, thread)


def test_last_backed_up_stays_out_of_the_settings_payload(serve, store):
    server = serve(store)
    get(server, "/api/database/backup")

    settings = json.loads(get(server, "/api/settings")[2])

    assert "last_backed_up" not in settings
