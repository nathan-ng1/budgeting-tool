import threading
from pathlib import Path

import pytest

from dashboard.server import build_server
from database.store import connect


@pytest.fixture
def serve():
    """Run a Dashboard server on a background thread for the duration of a test.

    Yields a factory so a test can choose its own `static_root` - in
    particular, one that has no built frontend in it, or a `changelog_path`
    pointing at a temporary file, or its own `env_path` / `pick_folder`
    stand-ins (ADR-0030).
    """
    running = []

    def _serve(
        store,
        static_root: Path | None = None,
        changelog_path: Path | None = None,
        env_path: Path | None = None,
        pick_folder=None,
    ):
        kwargs = {} if static_root is None else {"static_root": static_root}
        if changelog_path is not None:
            kwargs["changelog_path"] = changelog_path
        if env_path is not None:
            kwargs["env_path"] = env_path
        if pick_folder is not None:
            kwargs["pick_folder"] = pick_folder
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
