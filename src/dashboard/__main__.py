import os
from pathlib import Path

from dotenv import load_dotenv

from dashboard.server import build_server
from database import store as database_store

REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    port = int(os.environ.get("DASHBOARD_PORT", "8765"))

    store = database_store.connect()
    pending = store.pending_migration_names()
    if pending:
        # Never run them here: updating is a manual step (ADR-0019), and a
        # code pull without an update would otherwise fail every Transactions
        # read once the new columns are selected.
        store.close()
        raise SystemExit(
            f"The Database needs updating before the Dashboard can start (pending: {', '.join(pending)}). "
            "Run the update first (update.bat on Windows, update.command on macOS), then start the Dashboard again."
        )

    server = build_server(store, port=port)
    print(f"Dashboard serving on http://127.0.0.1:{server.server_port} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
