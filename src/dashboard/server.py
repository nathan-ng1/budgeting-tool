"""Thin HTTP layer over dashboard.queries, plus the built frontend - see
ADR-0008 (local web app, no data leaves the machine). Binds to localhost only.
"""

import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from dashboard import queries

# Where `npm run build` puts the frontend (see frontend/vite.config.js). The
# directory is a build artefact, so it is absent in a fresh clone until the
# frontend has been built once.
STATIC_ROOT = Path(__file__).resolve().parent / "static"

# Only what the build actually emits - see frontend/ (a page, its JS/CSS bundle,
# and the vendored fonts).
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript",
    ".css": "text/css",
    ".woff2": "font/woff2",
    ".svg": "image/svg+xml",
}

BUILD_INSTRUCTIONS = (
    "The Dashboard has not been built yet. Run `npm install` and `npm run build` "
    "in the repo's `frontend/` directory, then reload this page."
)


def build_server(store, host: str = "127.0.0.1", port: int = 0, static_root: Path = STATIC_ROOT) -> HTTPServer:
    # Single-threaded: the sqlite connection on `store` is not safe for
    # concurrent access, and this is a single local user - one request at a
    # time is fine.
    return HTTPServer((host, port), _make_handler(store, static_root))


def _make_handler(store, static_root: Path):
    class DashboardRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)

            if parsed.path == "/api/overview":
                self._serve_overview(parse_qs(parsed.query))
            elif parsed.path.startswith("/api/"):
                self._send_json(404, {"error": "Not found"})
            else:
                self._serve_static(parsed.path)

        def _serve_overview(self, params) -> None:
            try:
                year = int(params["year"][0])
                month = int(params["month"][0])
            except (KeyError, ValueError, IndexError):
                self._send_json(400, {"error": "year and month query parameters are required integers"})
                return

            overview = queries.get_month_overview(store, year=year, month=month)
            self._send_json(200, asdict(overview))

        def _serve_static(self, path: str) -> None:
            # The Dashboard is one page with no client-side router, so only "/"
            # serves it. Every other path is a real file or nothing at all -
            # falling back to index.html would answer a stale asset URL with
            # HTML the browser then rejects as the wrong MIME type.
            requested = self._resolve(path)

            if requested is None:
                self._send_plain(403, "Forbidden")
                return

            if path == "/":
                requested = static_root / "index.html"
                if not requested.is_file():
                    self._send_plain(501, BUILD_INSTRUCTIONS)
                    return

            if not requested.is_file():
                self._send_plain(404, "Not found")
                return

            self._send_bytes(200, requested.read_bytes(), CONTENT_TYPES.get(requested.suffix, "application/octet-stream"))

        def _resolve(self, path: str) -> Path | None:
            """The file `path` names inside the static root, or None if it
            points outside it (`..` traversal)."""
            relative = unquote(path).lstrip("/")
            candidate = (static_root / relative).resolve()
            root = static_root.resolve()

            if candidate != root and root not in candidate.parents:
                return None
            return candidate

        def log_message(self, format, *args):
            pass

        def _send_json(self, status: int, payload: dict) -> None:
            self._send_bytes(status, json.dumps(payload).encode("utf-8"), "application/json")

        def _send_plain(self, status: int, message: str) -> None:
            self._send_bytes(status, message.encode("utf-8"), "text/plain; charset=utf-8")

        def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return DashboardRequestHandler
