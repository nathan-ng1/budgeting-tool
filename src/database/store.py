import os
import sqlite3
from datetime import date, datetime
from pathlib import Path

from budget_suggestions.suggestion import BudgetSuggestion
from recurring.rules import RecurringRule, StoredRecurringRule
from transaction_log.categories import CATEGORIES_BY_TYPE, Category, require_valid_type_category_pair
from transaction_log.entries import Candidate, ExistingRow, Transaction

REPO_ROOT = Path(__file__).resolve().parents[2]

# `categories` is additive (CREATE TABLE IF NOT EXISTS), same as every other
# table here. `transactions`/`recurring_rules`/`category_budgets` are written
# below with their end-state `category_id` FK column already in place - see
# Issue #90's "Foreign-key migration" decision: on a brand new database (every
# test, every fresh install) CREATE TABLE IF NOT EXISTS builds the target
# schema directly, while an existing pre-#90 database (still `category` TEXT)
# needs `migration.categories_table.migrate` run once to add `category_id`,
# backfill it, and drop the old TEXT column before this code can read it.
SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    name TEXT NOT NULL UNIQUE,
    emoji TEXT,
    locked INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    amount REAL NOT NULL,
    type TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    notes TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recurring_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    type TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    notes TEXT NOT NULL,
    frequency TEXT NOT NULL,
    interval INTEGER NOT NULL,
    day TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT
);

CREATE TABLE IF NOT EXISTS category_budgets (
    category_id INTEGER NOT NULL REFERENCES categories(id),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    amount NUMERIC NOT NULL,
    PRIMARY KEY (category_id, year, month)
);

CREATE TABLE IF NOT EXISTS budget_suggestion (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    write_up TEXT NOT NULL,
    generated_at TEXT NOT NULL
);
"""


class RecurringRuleNotFound(LookupError):
    """No Recurring Transactions Config rule has the given id.

    Distinct from a ValueError over the rule's contents: the caller named a row
    that isn't there, rather than describing one badly.
    """


class TransactionNotFound(LookupError):
    """No Transaction has the given id.

    Distinct from a ValueError over the transaction's contents: the caller
    named a row that isn't there, rather than describing one badly.
    """


class LocalStore:
    """Live Transaction Log + Recurring Transactions Config store, backed by
    a local SQLite database.

    Mirrors FakeStore's shape (see tests/conftest.py).
    """

    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    def read_existing_rows(self) -> list[ExistingRow]:
        rows = self._connection.execute("SELECT date, amount, notes FROM transactions").fetchall()
        return [
            ExistingRow(date=date.fromisoformat(row_date), amount=amount, notes=notes)
            for row_date, amount, notes in rows
        ]

    def append_rows(self, candidates: list[Candidate]) -> None:
        if not candidates:
            return

        self._connection.executemany(
            "INSERT INTO transactions (date, amount, type, category_id, notes) VALUES (?, ?, ?, ?, ?)",
            [
                (c.date.isoformat(), round(c.stored_amount, 2), c.type, self._category_id(c.category), c.notes)
                for c in candidates
            ],
        )
        self._connection.commit()

    def read_transactions(self) -> list[Transaction]:
        rows = self._connection.execute(
            "SELECT t.id, t.date, t.amount, t.type, c.name, t.notes "
            "FROM transactions t JOIN categories c ON c.id = t.category_id"
        ).fetchall()
        return [
            Transaction(
                id=row_id,
                date=date.fromisoformat(row_date),
                amount=amount,
                type=transaction_type,
                category=category,
                notes=notes,
            )
            for row_id, row_date, amount, transaction_type, category, notes in rows
        ]

    def create_transaction(self, candidate: Candidate) -> Transaction:
        # Candidate.__post_init__ already validated the (Type, Category) pair
        # and the non-zero Amount - there is no invalid Candidate to reject.
        cursor = self._connection.execute(
            "INSERT INTO transactions (date, amount, type, category_id, notes) VALUES (?, ?, ?, ?, ?)",
            self._transaction_columns(candidate),
        )
        self._connection.commit()
        return _as_transaction(cursor.lastrowid, candidate)

    def update_transaction(self, transaction_id: int, candidate: Candidate) -> Transaction:
        cursor = self._connection.execute(
            "UPDATE transactions SET date = ?, amount = ?, type = ?, category_id = ?, notes = ? WHERE id = ?",
            (*self._transaction_columns(candidate), transaction_id),
        )
        if cursor.rowcount == 0:
            self._connection.rollback()
            raise TransactionNotFound(f"No Transaction has id {transaction_id}")

        self._connection.commit()
        return _as_transaction(transaction_id, candidate)

    def delete_transaction(self, transaction_id: int) -> None:
        cursor = self._connection.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        if cursor.rowcount == 0:
            self._connection.rollback()
            raise TransactionNotFound(f"No Transaction has id {transaction_id}")

        self._connection.commit()

    def append_recurring_rules(self, rules: list[RecurringRule]) -> None:
        if not rules:
            return

        self._connection.executemany(
            "INSERT INTO recurring_rules "
            "(amount, type, category_id, notes, frequency, interval, day, start_date, end_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [self._as_columns(rule) for rule in rules],
        )
        self._connection.commit()

    def read_recurring_rules(self) -> list[RecurringRule]:
        rows = self._connection.execute(
            "SELECT r.amount, r.type, c.name, r.notes, r.frequency, r.interval, r.day, r.start_date, r.end_date "
            "FROM recurring_rules r JOIN categories c ON c.id = r.category_id"
        ).fetchall()
        return [_as_rule(row) for row in rows]

    def read_stored_recurring_rules(self) -> list[StoredRecurringRule]:
        """Every rule with the id the Dashboard needs to edit or delete it.

        Ordered by id, so the CRUD screen lists rules in the order they were
        created rather than whatever order SQLite happens to return.
        """
        rows = self._connection.execute(
            "SELECT r.id, r.amount, r.type, c.name, r.notes, r.frequency, r.interval, r.day, r.start_date, r.end_date "
            "FROM recurring_rules r JOIN categories c ON c.id = r.category_id ORDER BY r.id"
        ).fetchall()
        return [StoredRecurringRule(id=row[0], rule=_as_rule(row[1:])) for row in rows]

    def create_recurring_rule(self, rule: RecurringRule) -> StoredRecurringRule:
        _validate_pair(rule)

        cursor = self._connection.execute(
            "INSERT INTO recurring_rules "
            "(amount, type, category_id, notes, frequency, interval, day, start_date, end_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            self._as_columns(rule),
        )
        self._connection.commit()
        return StoredRecurringRule(id=cursor.lastrowid, rule=rule)

    def update_recurring_rule(self, rule_id: int, rule: RecurringRule) -> StoredRecurringRule:
        _validate_pair(rule)

        cursor = self._connection.execute(
            "UPDATE recurring_rules SET "
            "amount = ?, type = ?, category_id = ?, notes = ?, frequency = ?, "
            "interval = ?, day = ?, start_date = ?, end_date = ? "
            "WHERE id = ?",
            (*self._as_columns(rule), rule_id),
        )
        if cursor.rowcount == 0:
            # Nothing was written, so nothing needs undoing - but leave the
            # transaction clean for the next caller either way.
            self._connection.rollback()
            raise RecurringRuleNotFound(f"No Recurring Transactions Config rule has id {rule_id}")

        self._connection.commit()
        return StoredRecurringRule(id=rule_id, rule=rule)

    def delete_recurring_rule(self, rule_id: int) -> None:
        cursor = self._connection.execute("DELETE FROM recurring_rules WHERE id = ?", (rule_id,))
        if cursor.rowcount == 0:
            self._connection.rollback()
            raise RecurringRuleNotFound(f"No Recurring Transactions Config rule has id {rule_id}")

        self._connection.commit()

    def read_category_budgets(self, year: int, month: int) -> dict[str, float]:
        """Every Category Budget set for one specific (year, month), keyed by
        Category. A Category with no Category Budget for this month is
        omitted - never reported as $0 (unset != $0).
        """
        rows = self._connection.execute(
            "SELECT c.name, cb.amount FROM category_budgets cb JOIN categories c ON c.id = cb.category_id "
            "WHERE cb.year = ? AND cb.month = ?",
            (year, month),
        ).fetchall()
        return {category: amount for category, amount in rows}

    def read_category_budgets_for_range(
        self, category: str, start_year: int, start_month: int, end_year: int, end_month: int
    ) -> dict[tuple[int, int], float]:
        """One Category's Category Budgets across an inclusive span of months,
        keyed by (year, month). A month with none set is omitted.
        """
        rows = self._connection.execute(
            "SELECT cb.year, cb.month, cb.amount FROM category_budgets cb JOIN categories c ON c.id = cb.category_id "
            "WHERE c.name = ? AND (cb.year * 12 + cb.month) BETWEEN (? * 12 + ?) AND (? * 12 + ?)",
            (category, start_year, start_month, end_year, end_month),
        ).fetchall()
        return {(year, month): amount for year, month, amount in rows}

    def upsert_category_budget(
        self, transaction_type: str, category: str, year: int, month: int, amount: float
    ) -> None:
        require_valid_type_category_pair(transaction_type, category)

        self._connection.execute(
            "INSERT INTO category_budgets (category_id, year, month, amount) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(category_id, year, month) DO UPDATE SET amount = excluded.amount",
            (self._category_id(category), year, month, amount),
        )
        self._connection.commit()

    def delete_category_budget(self, category: str, year: int, month: int) -> None:
        category_id = self._category_id_or_none(category)
        if category_id is None:
            # Nothing could reference an unknown Category anyway - a no-op,
            # same as deleting a budget that was simply never set.
            return

        self._connection.execute(
            "DELETE FROM category_budgets WHERE category_id = ? AND year = ? AND month = ?",
            (category_id, year, month),
        )
        self._connection.commit()

    def read_categories(self) -> list[Category]:
        """Every Category, sourced from the `categories` table (Issue #90) -
        the DB-backed replacement for the hardcoded CATEGORIES_BY_TYPE dict.
        """
        rows = self._connection.execute("SELECT id, type, name, emoji, locked FROM categories").fetchall()
        return [
            Category(id=row_id, type=row_type, name=name, emoji=emoji, locked=bool(locked))
            for row_id, row_type, name, emoji, locked in rows
        ]

    def _category_id(self, name: str) -> int:
        category_id = self._category_id_or_none(name)
        if category_id is None:
            raise ValueError(f"Category {name!r} does not exist")
        return category_id

    def _category_id_or_none(self, name: str) -> int | None:
        row = self._connection.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()
        return row[0] if row is not None else None

    def _transaction_columns(self, candidate: Candidate) -> tuple:
        return (
            candidate.date.isoformat(),
            candidate.amount,
            candidate.type,
            self._category_id(candidate.category),
            candidate.notes,
        )

    def _as_columns(self, rule: RecurringRule) -> tuple:
        return (
            rule.amount,
            rule.type,
            self._category_id(rule.category),
            rule.notes,
            rule.frequency,
            rule.interval,
            str(rule.day),
            rule.start_date.isoformat(),
            rule.end_date.isoformat() if rule.end_date is not None else None,
        )

    def write_budget_suggestion(self, write_up: str, generated_at: datetime) -> None:
        """Replace the one standing Budget Suggestion outright (ADR-0014) -
        `budget_suggestion` is a single-row table (CHECK (id = 1)), not a
        history table, so this is always an overwrite, never an append.
        """
        self._connection.execute(
            "INSERT INTO budget_suggestion (id, write_up, generated_at) VALUES (1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET write_up = excluded.write_up, generated_at = excluded.generated_at",
            (write_up, generated_at.isoformat()),
        )
        self._connection.commit()

    def read_budget_suggestion(self) -> BudgetSuggestion | None:
        """The current standing Budget Suggestion, or None if the script has
        never been run."""
        row = self._connection.execute(
            "SELECT write_up, generated_at FROM budget_suggestion WHERE id = 1"
        ).fetchone()
        if row is None:
            return None

        write_up, generated_at = row
        return BudgetSuggestion(write_up=write_up, generated_at=datetime.fromisoformat(generated_at))


def _as_transaction(transaction_id: int, candidate: Candidate) -> Transaction:
    return Transaction(
        id=transaction_id,
        date=candidate.date,
        amount=candidate.amount,
        type=candidate.type,
        category=candidate.category,
        notes=candidate.notes,
    )


def _validate_pair(rule: RecurringRule) -> None:
    """Reject a rule whose (Type, Category) pair isn't one this project allows.

    RecurringRule's own __post_init__ already vets the schedule (Frequency,
    Interval, Day against Start Date); the pair is the part it can't see.
    """
    require_valid_type_category_pair(rule.type, rule.category)


def _as_rule(columns) -> RecurringRule:
    amount, transaction_type, category, notes, frequency, interval, day, start_date, end_date = columns
    return RecurringRule(
        amount=amount,
        type=transaction_type,
        category=category,
        notes=notes,
        frequency=frequency,
        # Day is stored as text either way - a weekday name for Weekly rules,
        # a day-of-month for Monthly ones.
        day=int(day) if frequency == "Monthly" else day,
        interval=interval,
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date) if end_date is not None else None,
    )


def _seed_default_categories(connection: sqlite3.Connection) -> None:
    """Idempotent bootstrap of `categories` from CATEGORIES_BY_TYPE - safe to
    run on every connect() (INSERT OR IGNORE against `name`'s UNIQUE
    constraint), same as SCHEMA's own CREATE TABLE IF NOT EXISTS. This is what
    makes a fresh database (every test, every new install) immediately have a
    working `categories` table with no separate setup step - Beem Adjustment
    seeded locked (ADR-0015). A pre-#90 database that already has real
    Transaction/Recurring Rule/Category Budget rows still needs
    `migration.categories_table.migrate` run once to backfill their
    `category_id` from the old TEXT `category` column.
    """
    connection.executemany(
        "INSERT OR IGNORE INTO categories (type, name, locked) VALUES (?, ?, ?)",
        [
            (transaction_type, name, 1 if name == "Beem Adjustment" else 0)
            for transaction_type, names in CATEGORIES_BY_TYPE.items()
            for name in sorted(names)
        ],
    )
    connection.commit()


def connect(database_path: Path | None = None) -> LocalStore:
    """Build a LocalStore against the local SQLite database.

    Reads DATABASE_PATH from the environment (loaded from a repo-root `.env`
    if present) when database_path isn't given explicitly. Creates the
    categories/transactions/recurring_rules/category_budgets/budget_suggestion
    tables if they don't exist yet, and seeds `categories` with today's fixed
    Category list if it's empty.
    """
    if database_path is None:
        from dotenv import load_dotenv

        load_dotenv(REPO_ROOT / ".env")
        database_path = Path(os.environ["DATABASE_PATH"])

    database_path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: the Dashboard's local HTTP server handles each
    # connection on its own thread, so this connection is used from threads
    # other than the one that opened it. A lock in dashboard.server serialises
    # the handlers, so access stays one request at a time - never concurrent.
    connection = sqlite3.connect(database_path, check_same_thread=False)
    connection.executescript(SCHEMA)
    connection.commit()
    _seed_default_categories(connection)
    return LocalStore(connection=connection)
