"""The Retail Edition's launcher (Issue #249, spec #236, decisions S4, S10, S15,
S16): the entry point a Buyer double-clicks, kept apart from the Dashboard
server so the Collaborator Edition's terminal-launched Dashboard is unchanged.

`launch` resolves the Database location with the shared resolver, starts the
Dashboard on the usual port or the next free one, records that port in the
per-user data folder, and opens the default browser to it. A repeat launch finds
the recorded port, sees the Dashboard answering there, reopens the browser and
exits without starting a second server (so there is never a second writer on the
Database). Quit in Settings stops the server and clears the record.

There is no console window and no tray icon: the process is windowless and
prints nothing. The browser opener, port probe and running-instance check are
parameters so the entry function is tested without a real browser.
"""

import json
import socket
import threading
import webbrowser
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from dashboard.server import LAUNCHER_PATH, build_server
from database import location
from database import store as database_store

DEFAULT_PORT = 8765
# How many ports to try from the preferred one before giving up.
PORT_ATTEMPTS = 50
INSTANCE_FILE_NAME = "instance.json"
LOCALHOST = "127.0.0.1"


class NoFreePort(RuntimeError):
    pass


def instance_url(port: int) -> str:
    return f"http://{LOCALHOST}:{port}/"


def port_is_free(port: int) -> bool:
    """True if nothing is listening on `port` of localhost right now."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as probe:
        probe.settimeout(0.5)
        return probe.connect_ex((LOCALHOST, port)) != 0


def instance_running(port: int) -> bool:
    """True if this app's Dashboard, run by the launcher, answers on `port`."""
    try:
        with urlopen(f"http://{LOCALHOST}:{port}{LAUNCHER_PATH}", timeout=1) as response:
            return response.status == 200 and json.loads(response.read()).get("active") is True
    except (OSError, URLError, ValueError, AttributeError):
        return False


def read_instance(data_folder: Path) -> int | None:
    """The port the running instance recorded, or None if there is no usable record."""
    try:
        port = json.loads((data_folder / INSTANCE_FILE_NAME).read_text(encoding="utf-8"))["port"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return port if isinstance(port, int) and not isinstance(port, bool) else None


def write_instance(data_folder: Path, port: int) -> None:
    data_folder.mkdir(parents=True, exist_ok=True)
    (data_folder / INSTANCE_FILE_NAME).write_text(json.dumps({"port": port}), encoding="utf-8")


def clear_instance(data_folder: Path) -> None:
    (data_folder / INSTANCE_FILE_NAME).unlink(missing_ok=True)


def launch(
    *,
    data_folder: Path | None = None,
    preferred_port: int = DEFAULT_PORT,
    open_browser: Callable[[str], object] = webbrowser.open,
    port_is_free: Callable[[int], bool] = port_is_free,
    instance_running: Callable[[int], bool] = instance_running,
) -> None:
    """Start the Dashboard and open it, or reopen the one already running.
    Blocks while serving; returns once Quit stops the server."""
    data_folder = location.default_data_folder() if data_folder is None else data_folder

    recorded = read_instance(data_folder)
    if recorded is not None:
        if instance_running(recorded):
            open_browser(instance_url(recorded))
            return
        # A record left by an instance that died without clearing it.
        clear_instance(data_folder)

    store = database_store.connect(location.resolve_database_path(data_folder=data_folder))
    try:
        server, running_port = _bind(store, preferred_port, port_is_free, instance_running)
    except BaseException:
        store.close()
        raise
    if server is None:
        # The record was missing, but the app already answers on a port passed
        # on the way - e.g. a launch a moment ago that has not recorded yet.
        store.close()
        open_browser(instance_url(running_port))
        return

    port = server.server_port
    try:
        write_instance(data_folder, port)
        open_browser(instance_url(port))
        server.serve_forever()
    finally:
        if read_instance(data_folder) == port:
            clear_instance(data_folder)
        server.server_close()
        store.close()


def _bind(store, preferred_port, port_is_free, instance_running):
    """`(server, None)` bound to the first free port from `preferred_port`, or
    `(None, port)` if the app itself already answers on a port passed on the way."""
    for port in range(preferred_port, min(preferred_port + PORT_ATTEMPTS, 65536)):
        if not port_is_free(port):
            if instance_running(port):
                return None, port
            continue
        try:
            server = build_server(store, port=port, on_quit=lambda: _stop_soon(server))
        except OSError:
            # Free when probed, taken by the time we bound it.
            continue
        return server, None
    raise NoFreePort(f"No free port from {preferred_port} to {preferred_port + PORT_ATTEMPTS - 1}")


def _stop_soon(server) -> None:
    # `shutdown` waits for the serve loop to end, so it must not run on the
    # request thread that is answering Quit.
    threading.Thread(target=server.shutdown, daemon=True).start()


def main() -> None:
    launch()

