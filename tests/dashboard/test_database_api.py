"""The Settings tab's "Your data" endpoint and the swappable Database handle
(Issue #196, ADR-0030).

Exercised over real HTTP against real Databases in temporary folders.
"""

import json
from pathlib import Path
from urllib.request import urlopen

from dashboard.database_handle import DatabaseHandle
from dashboard.server import build_server
from database.store import connect


def get(server, path: str):
    with urlopen(f"http://127.0.0.1:{server.server_port}{path}") as response:
        return response.status, json.loads(response.read())


def test_the_database_location_and_size_on_disk_are_served(serve, store, tmp_path: Path):
    server = serve(store)

    status, body = get(server, "/api/database")

    database_file = (tmp_path / "budget.db").resolve()
    assert status == 200
    assert body == {"path": str(database_file), "size_bytes": database_file.stat().st_size, "last_backed_up": None}
    assert body["size_bytes"] > 0


def test_requests_after_a_swap_read_the_new_database(serve, store, tmp_path: Path):
    handle = DatabaseHandle(store)
    server = serve(handle)
    store.write_settings({"currency": "EUR"})
    other = connect(tmp_path / "elsewhere" / "other.db")
    other.write_settings({"currency": "GBP"})

    assert get(server, "/api/settings")[1]["currency"] == "EUR"
    handle.swap(other)

    assert get(server, "/api/settings")[1]["currency"] == "GBP"
    _status, location = get(server, "/api/database")
    assert location["path"] == str((tmp_path / "elsewhere" / "other.db").resolve())


def test_swapping_hands_back_the_old_store_so_the_caller_can_close_it(store, tmp_path: Path):
    handle = DatabaseHandle(store)

    old = handle.swap(connect(tmp_path / "other.db"))

    assert old is store
    old.close()  # releases the file, so it can be moved or deleted on Windows
    (tmp_path / "budget.db").unlink()


def test_the_env_path_and_folder_picker_can_be_injected(store, tmp_path: Path):
    def picker():
        return str(tmp_path)

    server = build_server(store, env_path=tmp_path / ".env", pick_folder=picker)
    try:
        assert server.env_path == tmp_path / ".env"
        assert server.pick_folder() == str(tmp_path)
    finally:
        server.server_close()


def test_the_env_path_and_folder_picker_default_to_the_real_ones(store):
    from dashboard.folder_picker import pick_folder
    from dashboard.server import ENV_PATH

    server = build_server(store)
    try:
        assert server.env_path == ENV_PATH
        assert ENV_PATH.name == ".env"
        assert server.pick_folder is pick_folder
    finally:
        server.server_close()
