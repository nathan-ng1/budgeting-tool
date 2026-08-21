"""Thin HTTP layer over dashboard.queries, plus the built frontend - see
ADR-0008 (local web app, no data leaves the machine). Binds to localhost only.
"""

import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from dashboard import queries, recurring, transactions
from database.store import RecurringRuleNotFound
from transaction_log.categories import CATEGORIES_BY_TYPE, types_with_categories

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

RECURRING_RULES_PATH = "/api/recurring-rules"
TRANSACTIONS_PATH = "/api/transactions"

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
            elif parsed.path == "/api/latest-transaction-date":
                # Dates the Transaction Log itself, for the header's "As at"
                # line - which is why it isn't part of the per-month Overview.
                latest = queries.get_latest_transaction_date(store)
                self._send_json(200, {"date": latest.isoformat() if latest is not None else None})
            elif parsed.path == RECURRING_RULES_PATH:
                self._send_json(200, [recurring.as_payload(r) for r in store.read_stored_recurring_rules()])
            elif parsed.path == TRANSACTIONS_PATH:
                self._serve_transactions(parse_qs(parsed.query))
            elif parsed.path == "/api/categories":
                # What the Settings screen's Type/Category selects offer, so
                # transaction_log.categories stays the one place the valid pairs
                # are stated rather than the frontend restating and drifting.
                self._send_json(
                    200, {t: sorted(CATEGORIES_BY_TYPE[t]) for t in types_with_categories()}
                )
            elif parsed.path.startswith("/api/"):
                self._send_json(404, {"error": "Not found"})
            else:
                self._serve_static(parsed.path)

        def do_POST(self):
            if urlparse(self.path).path != RECURRING_RULES_PATH:
                self._send_json(404, {"error": "Not found"})
                return

            self._write_rule(lambda rule: (201, store.create_recurring_rule(rule)))

        def do_PUT(self):
            rule_id = self._rule_id()
            if rule_id is None:
                self._send_json(404, {"error": "Not found"})
                return

            self._write_rule(lambda rule: (200, store.update_recurring_rule(rule_id, rule)))

        def do_DELETE(self):
            rule_id = self._rule_id()
            if rule_id is None:
                self._send_json(404, {"error": "Not found"})
                return

            try:
                store.delete_recurring_rule(rule_id)
            except RecurringRuleNotFound as cause:
                self._send_json(404, {"error": str(cause)})
                return

            self._send_bytes(204, b"", "application/json")


        def _rule_id(self) -> int | None:
            """The id in /api/recurring-rules/{id}, or None if this isn't that
            path - including when {id} isn't a number, since no rule can have
            that id either way."""
            path = urlparse(self.path).path
            prefix = f"{RECURRING_RULES_PATH}/"
            if not path.startswith(prefix):
                return None
            try:
                return int(path[len(prefix):])
            except ValueError:
                return None

        def _write_rule(self, write) -> None:
            """Parse a rule from the request body, hand it to `write`, and
            answer with the stored rule - or with why it couldn't be stored."""
            try:
                rule = recurring.from_payload(self._read_json())
            except ValueError as cause:
                self._send_json(400, {"error": str(cause)})
                return

            try:
                status, stored = write(rule)
            except RecurringRuleNotFound as cause:
                self._send_json(404, {"error": str(cause)})
                return
            except ValueError as cause:
                # An invalid (Type, Category) pair - the store is the one that
                # knows which pairs are allowed, so it decides, not this layer.
                self._send_json(400, {"error": str(cause)})
                return

            self._send_json(status, recurring.as_payload(stored))

        def _read_json(self):
            length = int(self.headers.get("Content-Length") or 0)
            try:
                return json.loads(self.rfile.read(length) or b"")
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise ValueError("Request body must be JSON") from None

        def _serve_overview(self, params) -> None:
            parsed = self._year_month(params)
            if parsed is None:
                return

            overview = queries.get_month_overview(store, year=parsed[0], month=parsed[1])
            self._send_json(200, asdict(overview))

        def _serve_transactions(self, params) -> None:
            parsed = self._year_month(params)
            if parsed is None:
                return

            rows = queries.get_financial_year_transactions(store, year=parsed[0], month=parsed[1])
            self._send_json(200, [transactions.as_payload(t) for t in rows])

        def _year_month(self, params) -> tuple[int, int] | None:
            """The (year, month) query params, or None - with a 400 already
            sent - if either is missing or not an integer."""
            try:
                return int(params["year"][0]), int(params["month"][0])
            except (KeyError, ValueError, IndexError):
                self._send_json(400, {"error": "year and month query parameters are required integers"})
                return None

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

        def _send_json(self, status: int, payload) -> None:
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
