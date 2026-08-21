import os
from pathlib import Path

from dotenv import load_dotenv

from dashboard.server import build_server
from database import store as database_store

REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    port = int(os.environ.get("DASHBOARD_PORT", "8765"))

    server = build_server(database_store.connect(), port=port)
    print(f"Dashboard serving on http://127.0.0.1:{server.server_port} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
