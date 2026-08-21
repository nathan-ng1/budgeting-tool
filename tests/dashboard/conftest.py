import threading
from pathlib import Path

import pytest

from dashboard.server import build_server
from database.store import connect


@pytest.fixture
def serve():
    """Run a Dashboard server on a background thread for the duration of a test.

    Yields a factory so a test can choose its own `static_root` - in
    particular, one that has no built frontend in it.
    """
    running = []

    def _serve(store, static_root: Path | None = None):
        kwargs = {} if static_root is None else {"static_root": static_root}
        server = build_server(store, **kwargs)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        running.append((server, thread))
        return server

    yield _serve

    for server, thread in running:
        server.shutdown()
        thread.join()
        server.server_close()


@pytest.fixture
def store(tmp_path: Path):
    return connect(tmp_path / "budget.db")
