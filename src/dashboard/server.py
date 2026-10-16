"""Thin HTTP layer over dashboard.queries, plus the built frontend - see
ADR-0008 (local web app, no data leaves the machine). Binds to localhost only.
"""

import json
import threading
from collections.abc import Callable
from dataclasses import asdict
from datetime import date, datetime
from functools import wraps
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as installed_version
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from dashboard import (
    budgets,
    categories,
    database_info,
    database_move,
    database_reset,
    goals,
    queries,
    recurring,
    settings,
    transactions,
)
from dashboard.changelog import read_history
from dashboard.database_handle import DatabaseHandle
from dashboard.folder_picker import FolderPickerError
from dashboard.folder_picker import pick_folder as real_pick_folder
from database import location
from database.store import CategoryNotFound, RecurringRuleNotFound, TransactionNotFound
from goals.goal import ARCHIVED, DELETED, GoalNotFound
from transaction_log import pipeline
from transaction_log.categories import type_lookup

# Where `npm run build` puts the frontend (see frontend/vite.config.js). The
# directory is a build artefact, so it is absent in a fresh clone until the
# frontend has been built once.
STATIC_ROOT = Path(__file__).resolve().parent / "static"

# The hand-curated Version History at the repo root (ADR-0029).
CHANGELOG_PATH = Path(__file__).resolve().parents[2] / "CHANGELOG.md"

# Only what the build actually emits - see frontend/ (a page, its JS/CSS bundle,
# and the vendored fonts).
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript",
    ".css": "text/css",
    ".woff2": "font/woff2",
    ".svg": "image/svg+xml",
}


DATABASE_PATH = "/api/database"
DATABASE_CHOOSE_FOLDER_PATH = f"{DATABASE_PATH}/choose-folder"
DATABASE_LOCATION_PATH = f"{DATABASE_PATH}/location"
DATABASE_BACKUP_PATH = f"{DATABASE_PATH}/backup"
DATABASE_RESET_SUMMARY_PATH = f"{DATABASE_PATH}/reset-summary"
DATABASE_RESET_PATH = f"{DATABASE_PATH}/reset"
RECURRING_RULES_PATH = "/api/recurring-rules"
RECURRING_RULES_RUN_PATH = f"{RECURRING_RULES_PATH}/run"
RECURRING_RULES_SPLIT_PATH = f"{RECURRING_RULES_PATH}/split"
TRANSACTIONS_PATH = "/api/transactions"
TRANSACTIONS_EXPORT_PATH = "/api/transactions/export"
TRANSACTIONS_IMPORT_TEMPLATE_PATH = "/api/transactions/import-template"
TRANSACTIONS_IMPORT_PREVIEW_PATH = "/api/transactions/import-preview"
TRANSACTIONS_IMPORT_COMMIT_PATH = "/api/transactions/import-commit"
BUDGET_EDITOR_PATH = "/api/budget-editor"
BUDGET_GRID_PATH = "/api/budget-grid"
BUDGET_SUGGESTION_PATH = "/api/budget-suggestion"
CATEGORIES_PATH = "/api/categories"
GOALS_PATH = "/api/goals"
GOALS_SPLIT_PATH = "/api/goals/split"
GOALS_SPLIT_PREVIEW_PATH = "/api/goals/split/preview"
SETTINGS_PATH = "/api/settings"
VERSION_PATH = "/api/version"

BUILD_INSTRUCTIONS = (
    "The Dashboard has not been built yet. Run `npm install` and `npm run build` "
    "in the repo's `frontend/` directory, then reload this page."
)


def _installed_version() -> str | None:
    try:
        return installed_version("budgeting-tool")
    except PackageNotFoundError:
        return None


def build_server(
    store,
    host: str = "127.0.0.1",
    port: int = 0,
    static_root: Path = STATIC_ROOT,
    changelog_path: Path = CHANGELOG_PATH,
    env_path: Path | None = None,
    data_folder: Path | None = None,
    pick_folder: Callable[[], str | None] = real_pick_folder,
    today: Callable[[], date] = date.today,
) -> ThreadingHTTPServer:
    # `store` may be a bare store or an already-built DatabaseHandle; handlers
    # always go through a handle, so the Database can be swapped while the
    # server keeps running (ADR-0030). `env_path`, `data_folder` (where the
    # pointer file lives, ADR-0032) and `pick_folder` are injectable so tests
    # can use a temporary `.env`, data folder and a stand-in dialog, and
    # `today` so the Goals figures can be pinned to a date.
    # Threaded, but one request at a time: `store_lock` serialises every
    # handler, so the sqlite connection on `store` is still only ever touched
    # by one request at once.
    #
    # A thread per connection is what stops a blank page. Browsers open
    # speculative "preconnect" sockets and send nothing on them; a
    # single-connection server accepts one, blocks reading a request line that
    # never arrives, and queues every real request behind it - index.html
    # arrives, its JS and CSS never do, and the page renders empty (Issue #45).
    database = store if isinstance(store, DatabaseHandle) else DatabaseHandle(store)
    server = ThreadingHTTPServer((host, port), _make_handler(database, static_root, changelog_path, today))
    server.env_path = location.ENV_PATH if env_path is None else env_path
    server.data_folder = data_folder
    server.pick_folder = pick_folder
    # Idle preconnect sockets must not keep the process alive at shutdown.
    server.daemon_threads = True
    return server


def _make_handler(store: DatabaseHandle, static_root: Path, changelog_path: Path, today: Callable[[], date]):
    # `store` is the swappable DatabaseHandle, which forwards to the open
    # LocalStore. Serialises the handlers, so they keep the
    # single-request-at-a-time access to it that its sqlite connection needs.
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
            elif parsed.path == "/api/transaction-date-range":
                # Bounds which years the Financial Year switcher offers
                # (ADR-0021) - the Transaction Log's actual span, not a
                # hardcoded lookback.
                earliest, latest = queries.get_transaction_date_range(store)
                self._send_json(
                    200,
                    {
                        "earliest": earliest.isoformat() if earliest is not None else None,
                        "latest": latest.isoformat() if latest is not None else None,
                    },
                )
            elif parsed.path == RECURRING_RULES_PATH:
                self._send_json(200, [recurring.as_payload(r) for r in store.read_stored_recurring_rules()])
            elif parsed.path == TRANSACTIONS_EXPORT_PATH:
                self._serve_transactions_export(parse_qs(parsed.query))
            elif parsed.path == TRANSACTIONS_IMPORT_TEMPLATE_PATH:
                self._serve_transactions_import_template()
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
            elif parsed.path == GOALS_PATH:
                # Every figure for every Goal, against one "today" so the Goals
                # tab and the Overview tile always agree (Goals spec section 7).
                self._send_json(200, goals.list_payload(
                        store.read_goals(), today(), store.read_goal_savings(), store.read_goal_contributions()
                    ))
            elif parsed.path == SETTINGS_PATH:
                self._send_json(200, settings.as_payload(store.read_settings()))
            elif parsed.path == DATABASE_PATH:
                if self._has_database_file():
                    self._send_json(200, database_info.as_payload(store.path, store.read_last_backed_up()))
            elif parsed.path == DATABASE_BACKUP_PATH:
                if self._has_database_file():
                    self._download_backup()
            elif parsed.path == DATABASE_RESET_SUMMARY_PATH:
                if self._has_database_file():
                    self._send_json(200, database_reset.summary_payload(store))
            elif parsed.path == VERSION_PATH:
                # The installed package's version (the `pyproject.toml` one,
                # refreshed by the update scripts' re-sync), so between
                # releases it is the last released Version (ADR-0029).
                # `history` is the parsed CHANGELOG.md, or null (still 200)
                # when it is missing or malformed.
                self._send_json(200, {"version": _installed_version(), "history": read_history(changelog_path)})
            elif parsed.path.startswith("/api/"):
                self._send_json(404, {"error": "Not found"})
            else:
                self._serve_static(parsed.path)

        def do_POST(self):
            if urlparse(self.path).path == DATABASE_CHOOSE_FOLDER_PATH:
                # Not under the lock: the folder dialog can stay open for as
                # long as the user likes, and must not freeze every request.
                self._choose_database_folder()
            else:
                self._post()

        @serialised
        def _post(self):
            path = urlparse(self.path).path
            if path == DATABASE_LOCATION_PATH:
                self._apply_database_folder()
            elif path == DATABASE_RESET_PATH:
                self._reset_database()
            elif path == RECURRING_RULES_RUN_PATH:
                self._run_recurring_rules()
            elif path == RECURRING_RULES_SPLIT_PATH:
                self._preview_split()
            elif path == RECURRING_RULES_PATH:
                self._write_rule(lambda rule: (201, store.create_recurring_rule(rule)))
            elif path == TRANSACTIONS_PATH:
                self._write_transaction(lambda candidate: (201, store.create_transaction(candidate)))
            elif path == CATEGORIES_PATH:
                self._create_category()
            elif path == GOALS_PATH:
                self._write_goal(lambda draft: (201, store.create_goal(draft)))
            elif (goal_action := self._goal_action()) is not None:
                self._archive_or_delete_goal(*goal_action)
            elif path == GOALS_SPLIT_PREVIEW_PATH:
                self._split_savings(write=False)
            elif path == GOALS_SPLIT_PATH:
                self._split_savings(write=True)
            elif (contribution_goal_id := self._id_after(GOALS_PATH, "/contributions")) is not None:
                self._add_contribution(contribution_goal_id)
            elif path == TRANSACTIONS_IMPORT_PREVIEW_PATH:
                self._import_preview()
            elif path == TRANSACTIONS_IMPORT_COMMIT_PATH:
                self._import_commit()
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

            goal_id = self._id_after(GOALS_PATH)
            if goal_id is not None:
                self._write_goal(lambda draft: (200, store.update_goal(goal_id, draft)))
                return

            if urlparse(self.path).path == SETTINGS_PATH:
                self._save_settings()
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

        def _id_after(self, prefix: str, suffix: str = "") -> int | None:
            """The id in `{prefix}/{id}{suffix}`, or None if this request's
            path isn't that shape - including when {id} isn't a number, since
            no row can have that id either way."""
            path = urlparse(self.path).path
            full_prefix = f"{prefix}/"
            if not (path.startswith(full_prefix) and path.endswith(suffix)):
                return None
            try:
                return int(path[len(full_prefix):len(path) - len(suffix)])
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

        def _preview_split(self) -> None:
            """The per-occurrence Amount a Total Amount would split into across
            the rule's schedule, without storing anything - so the add/edit
            form can show it before saving (Issue #148)."""
            try:
                rule, occurrences = recurring.split_from_payload(self._read_json())
            except ValueError as cause:
                self._send_json(400, {"error": str(cause)})
                return
            self._send_json(200, {"amount": rule.amount, "occurrences": occurrences})

        def _run_recurring_rules(self) -> None:
            """Manually expand every Recurring Transactions Config rule
            through today - the same expansion/dedupe path a Statement
            Export run already applies to its own rows, just with no
            candidates of its own (Issue #131)."""
            result = pipeline.run(candidates=[], store=store, through=date.today())
            self._send_json(200, {"written": len(result.to_write)})

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

        def _goal_action(self) -> tuple[int, str] | None:
            """(id, state) for `/api/goals/{id}/archive` or `/delete`, else None."""
            for action, state in (("archive", ARCHIVED), ("delete", DELETED)):
                goal_id = self._id_after(GOALS_PATH, f"/{action}")
                if goal_id is not None:
                    return goal_id, state
            return None

        def _send_goal(self, status: int, stored) -> None:
            """Answer with a stored Goal, its figures and its Contributions."""
            self._send_json(status, goals.as_payload(
                stored,
                today(),
                store.read_goal_savings().get(stored.id, 0.0),
                store.read_goal_contributions().get(stored.id),
            ))

        def _archive_or_delete_goal(self, goal_id: int, state: str) -> None:
            """Soft-move a Goal to Past goals; answer with it and its figures."""
            try:
                stored = store.set_goal_state(goal_id, state)
            except GoalNotFound as cause:
                self._send_json(404, {"error": str(cause)})
                return
            self._send_goal(200, stored)

        def _add_contribution(self, goal_id: int) -> None:
            """Write a Goals-Category Savings Transaction linked to the Goal
            (Goals spec section 8) and answer with it."""
            try:
                goal = store.read_goal(goal_id)
                candidate = goals.contribution_from_payload(goal, self._read_json())
                created = store.create_transaction(candidate)
            except GoalNotFound as cause:
                self._send_json(404, {"error": str(cause)})
                return
            except ValueError as cause:
                # The amount or date was unusable, or the store refused the
                # link (for example the Goal is not active).
                self._send_json(400, {"error": str(cause)})
                return

            self._send_json(201, transactions.as_payload(created))

        def _split_savings(self, write: bool) -> None:
            """Divide one total across active Goals (Goals spec section 9).
            The server computes the rows; a preview answers with them and
            stores nothing, a split writes them all in one database
            transaction (or none, on any failure)."""
            try:
                stored_goals = store.read_goals()
                candidates = goals.split_from_payload(self._read_json(), stored_goals)
                created = store.create_transactions(candidates) if write else None
            except ValueError as cause:
                self._send_json(400, {"error": str(cause)})
                return
            except Exception:
                # The store rolled the whole write back, so nothing was saved.
                self._send_json(500, {"error": "The split couldn't be saved, so nothing was written."})
                return

            self._send_json(201 if write else 200, {"rows": goals.split_rows_payload(candidates, stored_goals, created)})

        def _write_goal(self, write) -> None:
            """Parse a GoalDraft from the request body, hand it to `write`, and
            answer with the stored Goal and its figures - or with why it
            couldn't be stored."""
            try:
                draft = goals.draft_from_payload(self._read_json())
            except ValueError as cause:
                self._send_json(400, {"error": str(cause)})
                return

            try:
                status, stored = write(draft)
            except GoalNotFound as cause:
                self._send_json(404, {"error": str(cause)})
                return
            except ValueError as cause:
                # A title another Goal already uses - the store is the one that
                # can see the other Goals, so it decides.
                self._send_json(400, {"error": str(cause)})
                return

            self._send_goal(status, stored)

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

        def _import_preview(self) -> None:
            """Parse an uploaded Import workbook and answer with its
            per-row report, writing nothing (Issue #98)."""
            try:
                file_bytes = transactions.decode_import_file(self._read_json())
            except ValueError as cause:
                self._send_json(400, {"error": str(cause)})
                return

            try:
                report = transactions.preview_import(file_bytes, store.read_categories(), store.read_existing_rows())
            except ValueError as cause:
                self._send_json(400, {"error": str(cause)})
                return

            self._send_json(200, report)

        def _import_commit(self) -> None:
            """Write exactly the to-write Candidate list an Import preview
            handed back - re-resolved against the store's *current* rows, so
            a row that became a duplicate since preview is skipped rather
            than double-written (Issue #98)."""
            try:
                candidates = transactions.candidates_from_import_payload(self._read_json())
            except ValueError as cause:
                self._send_json(400, {"error": str(cause)})
                return

            to_write = transactions.resolve_commit(candidates, store.read_existing_rows())
            try:
                store.append_rows(to_write)
            except ValueError as cause:
                # A Category referenced by the preview was renamed or deleted
                # in the meantime - the store is the authority on why the
                # write is refused.
                self._send_json(400, {"error": str(cause)})
                return

            self._send_json(200, {"written": [transactions.as_candidate_payload(c) for c in to_write]})

        def _choose_database_folder(self) -> None:
            """Open the native folder picker and report what the chosen folder
            holds (ADR-0030). Changes nothing: the user confirms first. Only
            the inspection holds the lock, not the dialog."""
            try:
                chosen = self.server.pick_folder()
                if chosen is None:
                    self._send_json(200, {"cancelled": True})
                    return
                with store_lock:
                    if not self._has_database_file():
                        return
                    report = database_move.inspect_folder(chosen, Path(store.path))
            except FolderPickerError as cause:
                self._send_json(500, {"error": str(cause)})
                return
            except database_move.FolderUnusable as cause:
                self._send_json(400, {"error": str(cause)})
                return

            self._send_json(200, database_move.report_payload(report))

        def _apply_database_folder(self) -> None:
            """Carry out the confirmed choice of folder - move the Database
            there, or switch to the one already in it (migrating it first if
            it is older) - and answer with the Database's new location, plus
            any old files a move could not remove."""
            if not self._has_database_file():
                return
            try:
                folder = self._read_json().get("folder")
                if not isinstance(folder, str) or not folder:
                    raise database_move.FolderUnusable("Choose a folder first")
                left_behind = database_move.apply_folder(
                    store, folder, self.server.env_path, data_folder=self.server.data_folder
                )
            except (ValueError, AttributeError) as cause:
                # FolderUnusable is a ValueError, like an unreadable body.
                self._send_json(400, {"error": str(cause)})
                return
            except database_move.MoveFailed as cause:
                self._send_json(500, {"error": str(cause)})
                return

            payload = database_info.as_payload(store.path)
            if left_behind:
                payload["left_behind"] = [str(path) for path in left_behind]
            self._send_json(200, payload)

        def _has_database_file(self) -> bool:
            """True if the open store is a file-backed Database; otherwise
            answers 400 (e.g. a store built without a path)."""
            if store.path is None:
                self._send_json(400, {"error": "The Dashboard isn't using a Database file"})
                return False
            return True

        def _reset_database(self) -> None:
            """Delete all data and serve a fresh empty Database at the same
            path - but only with the typed confirmation (Issue #201)."""
            if not self._has_database_file():
                return
            try:
                database_reset.check_confirmation(self._read_json())
            except ValueError as cause:
                # ConfirmationMissing, or an unreadable body.
                self._send_json(400, {"error": str(cause)})
                return

            try:
                database_reset.reset(store)
            except database_reset.ResetFailed as cause:
                self._send_json(500, {"error": str(cause)})
                return

            self._send_json(200, database_info.as_payload(store.path))

        def _save_settings(self) -> None:
            """Save any subset of the localisation settings (ADR-0027) and
            answer with all of them - or with why the save was refused."""
            try:
                updates = settings.updates_from_payload(self._read_json())
            except ValueError as cause:
                self._send_json(400, {"error": str(cause)})
                return

            store.write_settings(updates)
            self._send_json(200, settings.as_payload(store.read_settings()))

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
            start_month = self._period_start_month(params)
            if start_month is None:
                return

            overview = queries.get_annual_overview(store, year=year, start_month=start_month)
            self._send_json(200, asdict(overview))

        def _serve_transactions(self, params) -> None:
            parsed = self._year_month(params)
            if parsed is None:
                return

            rows = queries.get_financial_year_transactions(store, year=parsed[0], month=parsed[1])
            self._send_json(200, [transactions.as_payload(t) for t in rows])

        def _serve_transactions_export(self, params) -> None:
            parsed = self._date_range(params)
            if parsed is None:
                return
            start, end = parsed

            rows = queries.get_transactions_in_range(store, start, end)
            body = transactions.as_csv(rows)
            self._send_csv(body, filename=f"transactions_{start.isoformat()}_to_{end.isoformat()}.csv")

        def _serve_transactions_import_template(self) -> None:
            # Generated fresh from the live Category list on every request
            # (Issue #97) - never cached, so a Category added, renamed, or
            # removed via Category Management shows up with no restart.
            body = transactions.as_import_template(store.read_categories())
            self._send_xlsx(body, filename="transaction_import_template.xlsx")

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
            start_month = self._period_start_month(params)
            if start_month is None:
                return

            rows = queries.get_full_year_budget_grid(store, year=year, start_month=start_month)
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

        def _period_start_month(self, params) -> int | None:
            """The `period` query param translated to a start month (the saved
            Financial Year start month - July until one is saved - for
            `financial`, 1 for `calendar`) - defaulting to `financial` when
            omitted (ADR-0021, ADR-0027). None - with a 400 already sent - if
            `period` is present but neither value."""
            period = params.get("period", ["financial"])[0]
            if period == "financial":
                return settings.financial_year_start_month(store.read_settings())
            if period == "calendar":
                return 1
            self._send_json(400, {"error": "period query parameter must be 'financial' or 'calendar'"})
            return None

        def _date_range(self, params) -> tuple[date, date] | None:
            """The (start, end) query params as dates, or None - with a 400
            already sent - if either is missing or not a YYYY-MM-DD date."""
            try:
                start = date.fromisoformat(params["start"][0])
                end = date.fromisoformat(params["end"][0])
            except (KeyError, ValueError, IndexError):
                self._send_json(400, {"error": "start and end query parameters are required dates (YYYY-MM-DD)"})
                return None
            return start, end

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

        def _send_csv(self, body: bytes, filename: str) -> None:
            # Content-Disposition: attachment is what lets the Export panel's
            # download control be a plain <a href> - no fetch+blob flow needed
            # (Issue #96).
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _download_backup(self) -> None:
            # A Backup, not a raw copy of the open file (Issue #197, ADR-0030);
            # reused by the delete flow's "download a Backup first" (Issue #201).
            body, filename = database_info.make_backup(store, datetime.now().astimezone())
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.sqlite3")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_xlsx(self, body: bytes, filename: str) -> None:
            # Mirrors _send_csv: Content-Disposition: attachment lets the
            # Import panel's "Download template" control be a plain <a href>
            # (Issue #97).
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return DashboardRequestHandler
