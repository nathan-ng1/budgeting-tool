"""Thin HTTP layer over dashboard.queries, plus the built frontend - see
ADR-0008 (local web app, no data leaves the machine). Binds to localhost only.
"""

import json
import threading
from dataclasses import asdict
from functools import wraps
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from dashboard import budgets, categories, queries, recurring, transactions
from database.store import CategoryNotFound, RecurringRuleNotFound, TransactionNotFound
from transaction_log.categories import type_lookup

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
BUDGET_EDITOR_PATH = "/api/budget-editor"
BUDGET_GRID_PATH = "/api/budget-grid"
BUDGET_SUGGESTION_PATH = "/api/budget-suggestion"
CATEGORIES_PATH = "/api/categories"

BUILD_INSTRUCTIONS = (
    "The Dashboard has not been built yet. Run `npm install` and `npm run build` "
    "in the repo's `frontend/` directory, then reload this page."
)


def build_server(store, host: str = "127.0.0.1", port: int = 0, static_root: Path = STATIC_ROOT) -> ThreadingHTTPServer:
    # Threaded, but one request at a time: `store_lock` serialises every
    # handler, so the sqlite connection on `store` is still only ever touched
    # by one request at once.
    #
    # A thread per connection is what stops a blank page. Browsers open
    # speculative "preconnect" sockets and send nothing on them; a
    # single-connection server accepts one, blocks reading a request line that
    # never arrives, and queues every real request behind it - index.html
    # arrives, its JS and CSS never do, and the page renders empty (Issue #45).
    server = ThreadingHTTPServer((host, port), _make_handler(store, static_root))
    # Idle preconnect sockets must not keep the process alive at shutdown.
    server.daemon_threads = True
    return server


def _make_handler(store, static_root: Path):
    # Serialises the handlers, so they keep the single-request-at-a-time access
    # to `store` that its sqlite connection needs.
    store_lock = threading.Lock()

    def serialised(method):
        """Run `method` under `store_lock`.

        Deliberately wraps the dispatch only, not the socket read that precedes
        it: a browser preconnect socket sits open having sent nothing, and
        holding the lock across that read would block every other request
        exactly as the single-connection server used to (Issue #45).
        """

        @wraps(method)
        def wrapper(self):
            with store_lock:
                return method(self)

        return wrapper

    class DashboardRequestHandler(BaseHTTPRequestHandler):
        @serialised
        def do_GET(self):
            parsed = urlparse(self.path)

            if parsed.path == "/api/overview":
                self._serve_overview(parse_qs(parsed.query))
            elif parsed.path == "/api/annual-overview":
                self._serve_annual_overview(parse_qs(parsed.query))
            elif parsed.path == "/api/latest-transaction-date":
                # Dates the Transaction Log itself, for the header's "As at"
                # line - which is why it isn't part of the per-month Overview.
                latest = queries.get_latest_transaction_date(store)
                self._send_json(200, {"date": latest.isoformat() if latest is not None else None})
            elif parsed.path == RECURRING_RULES_PATH:
                self._send_json(200, [recurring.as_payload(r) for r in store.read_stored_recurring_rules()])
            elif parsed.path == TRANSACTIONS_PATH:
                self._serve_transactions(parse_qs(parsed.query))
            elif parsed.path == BUDGET_EDITOR_PATH:
                self._serve_budget_editor(parse_qs(parsed.query))
            elif parsed.path == BUDGET_GRID_PATH:
                self._serve_budget_grid(parse_qs(parsed.query))
            elif parsed.path == BUDGET_SUGGESTION_PATH:
                # Not scoped to a (year, month) - the one standing write-up
                # renders identically no matter which month pill is selected
                # (Issue #66).
                self._send_json(200, budgets.as_suggestion_payload(store.read_budget_suggestion()))
            elif parsed.path == CATEGORIES_PATH:
                # Every Category, id/type/name/emoji/locked (Issue #91) -
                # consumers that need the old {Type: [name, ...]} grouping for
                # a Type/Category select derive it from this flat list
                # themselves.
                self._send_json(200, [categories.as_payload(c) for c in store.read_categories()])
            elif parsed.path.startswith("/api/"):
                self._send_json(404, {"error": "Not found"})
            else:
                self._serve_static(parsed.path)

        @serialised
        def do_POST(self):
            path = urlparse(self.path).path
            if path == RECURRING_RULES_PATH:
                self._write_rule(lambda rule: (201, store.create_recurring_rule(rule)))
            elif path == TRANSACTIONS_PATH:
                self._write_transaction(lambda candidate: (201, store.create_transaction(candidate)))
            elif path == CATEGORIES_PATH:
                self._create_category()
            else:
                self._send_json(404, {"error": "Not found"})

        @serialised
        def do_PUT(self):
            rule_id = self._id_after(RECURRING_RULES_PATH)
            if rule_id is not None:
                self._write_rule(lambda rule: (200, store.update_recurring_rule(rule_id, rule)))
                return

            transaction_id = self._id_after(TRANSACTIONS_PATH)
            if transaction_id is not None:
                self._write_transaction(
                    lambda candidate: (200, store.update_transaction(transaction_id, candidate))
                )
                return

            category_id = self._id_after(CATEGORIES_PATH)
            if category_id is not None:
                self._update_category(category_id)
                return

            category = self._category_after(BUDGET_EDITOR_PATH)
            if category is not None:
                self._write_category_budget(category)
                return

            self._send_json(404, {"error": "Not found"})

        @serialised
        def do_DELETE(self):
            rule_id = self._id_after(RECURRING_RULES_PATH)
            if rule_id is not None:
                try:
                    store.delete_recurring_rule(rule_id)
                except RecurringRuleNotFound as cause:
                    self._send_json(404, {"error": str(cause)})
                    return
                self._send_bytes(204, b"", "application/json")
                return

            transaction_id = self._id_after(TRANSACTIONS_PATH)
            if transaction_id is not None:
                try:
                    store.delete_transaction(transaction_id)
                except TransactionNotFound as cause:
                    self._send_json(404, {"error": str(cause)})
                    return
                self._send_bytes(204, b"", "application/json")
                return

            category_id = self._id_after(CATEGORIES_PATH)
            if category_id is not None:
                try:
                    store.delete_category(category_id)
                except CategoryNotFound as cause:
                    self._send_json(404, {"error": str(cause)})
                    return
                except ValueError as cause:
                    # CategoryLocked or CategoryInUse - the store is the
                    # authority on why a delete is refused.
                    self._send_json(400, {"error": str(cause)})
                    return
                self._send_bytes(204, b"", "application/json")
                return

            category = self._category_after(BUDGET_EDITOR_PATH)
            if category is not None:
                parsed = self._year_month(parse_qs(urlparse(self.path).query))
                if parsed is None:
                    return
                store.delete_category_budget(category, parsed[0], parsed[1])
                self._send_bytes(204, b"", "application/json")
                return

            self._send_json(404, {"error": "Not found"})

        def _id_after(self, prefix: str) -> int | None:
            """The id in `{prefix}/{id}`, or None if this request's path isn't
            that shape - including when {id} isn't a number, since no row can
            have that id either way."""
            path = urlparse(self.path).path
            full_prefix = f"{prefix}/"
            if not path.startswith(full_prefix):
                return None
            try:
                return int(path[len(full_prefix):])
            except ValueError:
                return None

        def _category_after(self, prefix: str) -> str | None:
            """The Category in `{prefix}/{category}`, or None if this
            request's path isn't that shape. Unquoted, since a Category can
            contain spaces and `&` (e.g. "Dining & Takeaway")."""
            path = urlparse(self.path).path
            full_prefix = f"{prefix}/"
            if not path.startswith(full_prefix):
                return None
            return unquote(path[len(full_prefix):])

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

        def _write_transaction(self, write) -> None:
            """Parse a Candidate from the request body, hand it to `write`, and
            answer with the stored Transaction - or with why it couldn't be
            stored."""
            try:
                candidate = transactions.from_payload(self._read_json())
            except ValueError as cause:
                self._send_json(400, {"error": str(cause)})
                return

            try:
                status, stored = write(candidate)
            except TransactionNotFound as cause:
                self._send_json(404, {"error": str(cause)})
                return
            except ValueError as cause:
                self._send_json(400, {"error": str(cause)})
                return

            self._send_json(status, transactions.as_payload(stored))

        def _create_category(self) -> None:
            try:
                transaction_type, name, emoji = categories.create_from_payload(self._read_json())
            except ValueError as cause:
                self._send_json(400, {"error": str(cause)})
                return

            try:
                created = store.create_category(transaction_type, name, emoji)
            except ValueError as cause:
                self._send_json(400, {"error": str(cause)})
                return

            self._send_json(201, categories.as_payload(created))

        def _update_category(self, category_id: int) -> None:
            try:
                name, emoji = categories.update_from_payload(self._read_json())
            except ValueError as cause:
                self._send_json(400, {"error": str(cause)})
                return

            try:
                updated = store.update_category(category_id, name, emoji)
            except CategoryNotFound as cause:
                self._send_json(404, {"error": str(cause)})
                return
            except ValueError as cause:
                # CategoryLocked, or a name collision - the store is the
                # authority on why the rename is refused.
                self._send_json(400, {"error": str(cause)})
                return

            self._send_json(200, categories.as_payload(updated))

        def _write_category_budget(self, category: str) -> None:
            """Parse an Amount from the request body and upsert this
            Category's Category Budget for the (year, month) query params."""
            parsed = self._year_month(parse_qs(urlparse(self.path).query))
            if parsed is None:
                return
            year, month = parsed

            transaction_type = type_lookup(store.read_categories()).get(category)
            if transaction_type is None:
                self._send_json(400, {"error": f"Category {category!r} is not a valid Category"})
                return

            try:
                amount = budgets.amount_from_payload(self._read_json())
            except ValueError as cause:
                self._send_json(400, {"error": str(cause)})
                return

            try:
                store.upsert_category_budget(transaction_type, category, year, month, amount)
            except ValueError as cause:
                self._send_json(400, {"error": str(cause)})
                return

            self._send_json(200, {"category": category, "amount": amount})

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

        def _serve_annual_overview(self, params) -> None:
            year = self._year(params)
            if year is None:
                return

            overview = queries.get_annual_overview(store, year=year)
            self._send_json(200, asdict(overview))

        def _serve_transactions(self, params) -> None:
            parsed = self._year_month(params)
            if parsed is None:
                return

            rows = queries.get_financial_year_transactions(store, year=parsed[0], month=parsed[1])
            self._send_json(200, [transactions.as_payload(t) for t in rows])

        def _serve_budget_editor(self, params) -> None:
            parsed = self._year_month(params)
            if parsed is None:
                return

            year, month = parsed
            window = self._query_int(params, "window")
            if window is None:
                window = budgets.DEFAULT_TRAILING_WINDOW

            try:
                rows = queries.get_budget_editor(store, year=year, month=month, trailing_months=window)
            except ValueError as cause:
                self._send_json(400, {"error": str(cause)})
                return

            self._send_json(200, budgets.as_editor_payload(rows))

        def _serve_budget_grid(self, params) -> None:
            year = self._year(params)
            if year is None:
                return

            rows = queries.get_full_year_budget_grid(store, year=year)
            self._send_json(200, budgets.as_grid_payload(rows))

        def _query_int(self, params, key: str) -> int | None:
            """The int value of query param `key`, or None if it's missing or
            not an integer - no response sent, callers decide the error."""
            try:
                return int(params[key][0])
            except (KeyError, ValueError, IndexError):
                return None

        def _year_month(self, params) -> tuple[int, int] | None:
            """The (year, month) query params, or None - with a 400 already
            sent - if either is missing or not an integer."""
            year, month = self._query_int(params, "year"), self._query_int(params, "month")
            if year is None or month is None:
                self._send_json(400, {"error": "year and month query parameters are required integers"})
                return None
            return year, month

        def _year(self, params) -> int | None:
            """The `year` query param, or None - with a 400 already sent - if
            it's missing or not an integer."""
            year = self._query_int(params, "year")
            if year is None:
                self._send_json(400, {"error": "year query parameter is required and must be an integer"})
                return None
            return year

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
